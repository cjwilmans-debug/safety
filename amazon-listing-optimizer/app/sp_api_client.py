"""
Amazon Selling Partner API (SP-API) Client.
Handles API requests to fetch listing data, reports, etc.
"""
import httpx
from typing import Optional, Any
from datetime import datetime

from .config import get_settings, AmazonOAuthConfig
from .oauth import amazon_oauth


class SPAPIClient:
    """Amazon SP-API client for fetching listing and catalog data."""

    def __init__(self, marketplace: str = "US"):
        self.settings = get_settings()
        self.marketplace = marketplace
        self.marketplace_id = AmazonOAuthConfig.MARKETPLACE_IDS.get(marketplace, "ATVPDKIKX0DER")
        self.endpoint = AmazonOAuthConfig.get_endpoint(marketplace)

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated request to SP-API."""
        access_token = await amazon_oauth.get_valid_access_token()

        if not access_token:
            raise Exception("No valid access token. Please authenticate first.")

        url = f"{self.endpoint}{path}"

        headers = {
            "x-amz-access-token": access_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30.0,
            )

            if response.status_code == 403:
                raise Exception("Access forbidden. Check your SP-API permissions.")
            elif response.status_code == 401:
                raise Exception("Unauthorized. Token may be invalid or expired.")
            elif response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise Exception(f"API error {response.status_code}: {error_data}")

            return response.json() if response.content else {}

    async def get_catalog_item(self, asin: str) -> dict:
        """
        Get catalog item details for a specific ASIN.
        Uses Catalog Items API v2022-04-01.
        """
        path = f"/catalog/2022-04-01/items/{asin}"
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": "attributes,identifiers,images,productTypes,summaries",
        }

        return await self._make_request("GET", path, params=params)

    async def search_catalog_items(
        self,
        keywords: Optional[str] = None,
        brand_names: Optional[list[str]] = None,
        limit: int = 20,
    ) -> dict:
        """
        Search catalog items.
        Uses Catalog Items API v2022-04-01.
        """
        path = "/catalog/2022-04-01/items"
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": "attributes,identifiers,images,productTypes,summaries",
            "pageSize": limit,
        }

        if keywords:
            params["keywords"] = keywords
        if brand_names:
            params["brandNames"] = ",".join(brand_names)

        return await self._make_request("GET", path, params=params)

    async def get_listings_item(self, seller_id: str, sku: str) -> dict:
        """
        Get listings item details for a specific SKU.
        Uses Listings Items API v2021-08-01.
        """
        path = f"/listings/2021-08-01/items/{seller_id}/{sku}"
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": "summaries,attributes,issues,offers,fulfillmentAvailability",
        }

        return await self._make_request("GET", path, params=params)

    async def get_my_listings(self, seller_id: str) -> dict:
        """
        Get all listings for a seller.
        Note: This requires seller authorization and appropriate permissions.
        """
        # This would use the Reports API to get a full catalog
        # For now, returning a placeholder structure
        return {
            "message": "Use Reports API to fetch full catalog",
            "seller_id": seller_id,
            "marketplace_id": self.marketplace_id,
        }

    async def get_a_plus_content(self, asin: str) -> dict:
        """
        Get A+ Content for a specific ASIN.
        Uses A+ Content API v2020-11-01.
        """
        path = "/aplus/2020-11-01/contentDocuments"
        params = {
            "marketplaceId": self.marketplace_id,
            "asin": asin,
        }

        return await self._make_request("GET", path, params=params)

    async def create_report(self, report_type: str) -> dict:
        """
        Create a report request.
        Common report types:
        - GET_MERCHANT_LISTINGS_ALL_DATA
        - GET_FLAT_FILE_OPEN_LISTINGS_DATA
        - GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT
        """
        path = "/reports/2021-06-30/reports"
        data = {
            "reportType": report_type,
            "marketplaceIds": [self.marketplace_id],
        }

        return await self._make_request("POST", path, json_data=data)

    async def get_report(self, report_id: str) -> dict:
        """Get report status and details."""
        path = f"/reports/2021-06-30/reports/{report_id}"
        return await self._make_request("GET", path)

    async def get_report_document(self, report_document_id: str) -> dict:
        """Get the URL to download a report document."""
        path = f"/reports/2021-06-30/documents/{report_document_id}"
        return await self._make_request("GET", path)


class ListingAnalyzer:
    """Analyzes listing data and generates optimization recommendations."""

    def __init__(self, marketplace: str = "US"):
        self.client = SPAPIClient(marketplace)
        self.marketplace = marketplace

    async def analyze_listing(self, asin: str) -> dict:
        """
        Analyze a single listing and return optimization scores.
        """
        try:
            catalog_data = await self.client.get_catalog_item(asin)
        except Exception as e:
            return {"error": str(e), "asin": asin}

        # Extract relevant data
        item = catalog_data.get("items", [{}])[0] if "items" in catalog_data else catalog_data

        analysis = {
            "asin": asin,
            "marketplace": self.marketplace,
            "analyzed_at": datetime.utcnow().isoformat(),
            "scores": {},
            "recommendations": [],
        }

        # Analyze title
        title_score = self._analyze_title(item)
        analysis["scores"]["title"] = title_score

        # Analyze images
        image_score = self._analyze_images(item)
        analysis["scores"]["images"] = image_score

        # Analyze attributes/bullets
        bullet_score = self._analyze_bullets(item)
        analysis["scores"]["bullets"] = bullet_score

        # Overall score
        scores = list(analysis["scores"].values())
        analysis["scores"]["overall"] = sum(s["score"] for s in scores) / len(scores) if scores else 0

        return analysis

    def _analyze_title(self, item: dict) -> dict:
        """Analyze product title."""
        summaries = item.get("summaries", [])
        title = summaries[0].get("itemName", "") if summaries else ""

        score = 0
        issues = []
        recommendations = []

        if title:
            # Check length (optimal: 150-200 characters for most categories)
            title_len = len(title)
            if title_len < 80:
                issues.append("Title too short - missing keyword opportunities")
                recommendations.append("Expand title to include more relevant keywords (target 150-200 chars)")
            elif title_len > 200:
                issues.append("Title may be too long - could be truncated on mobile")
                recommendations.append("Consider condensing title for better mobile display")
            else:
                score += 30

            # Check for brand at beginning
            if summaries and summaries[0].get("brand"):
                brand = summaries[0]["brand"]
                if title.lower().startswith(brand.lower()):
                    score += 20
                else:
                    issues.append("Brand not at the beginning of title")
                    recommendations.append("Move brand name to the start of the title")

            # Basic keyword density check (simplified)
            words = title.split()
            if len(words) >= 5:
                score += 20

            # Check for all caps (bad practice)
            if title.isupper():
                issues.append("Title is all caps - violates Amazon style guidelines")
                recommendations.append("Use proper title case for better readability")
            else:
                score += 15

            # Check for special characters overuse
            special_chars = sum(1 for c in title if c in "!@#$%^&*()[]{}|")
            if special_chars > 3:
                issues.append("Too many special characters in title")
            else:
                score += 15
        else:
            issues.append("No title found")
            recommendations.append("Add a keyword-rich product title")

        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "current_value": title,
        }

    def _analyze_images(self, item: dict) -> dict:
        """Analyze product images."""
        images = item.get("images", [])

        # Flatten image list if nested
        all_images = []
        for img_group in images:
            if isinstance(img_group, dict) and "images" in img_group:
                all_images.extend(img_group["images"])
            elif isinstance(img_group, dict):
                all_images.append(img_group)

        score = 0
        issues = []
        recommendations = []

        image_count = len(all_images)

        if image_count == 0:
            issues.append("No images found")
            recommendations.append("Add at least 7 high-quality images")
        elif image_count < 5:
            score += 20
            issues.append(f"Only {image_count} images - below optimal")
            recommendations.append("Add more images (target 7-9 images)")
        elif image_count < 7:
            score += 50
            recommendations.append("Consider adding lifestyle and infographic images")
        else:
            score += 80

        # Check for main image
        main_images = [img for img in all_images if img.get("variant") == "MAIN"]
        if main_images:
            score += 10
        else:
            issues.append("No main image variant identified")

        # Check image types/variants
        variants = set(img.get("variant", "UNKNOWN") for img in all_images)
        if len(variants) > 3:
            score += 10
        else:
            recommendations.append("Add variety: lifestyle, infographic, size chart images")

        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "image_count": image_count,
            "variants": list(variants),
        }

    def _analyze_bullets(self, item: dict) -> dict:
        """Analyze bullet points."""
        attributes = item.get("attributes", {})
        bullets = attributes.get("bullet_point", [])

        score = 0
        issues = []
        recommendations = []

        if not bullets:
            issues.append("No bullet points found")
            recommendations.append("Add 5 benefit-driven bullet points")
            return {
                "score": 0,
                "issues": issues,
                "recommendations": recommendations,
                "bullet_count": 0,
            }

        bullet_count = len(bullets)

        if bullet_count < 3:
            score += 20
            issues.append(f"Only {bullet_count} bullet points")
            recommendations.append("Add more bullet points (target 5)")
        elif bullet_count < 5:
            score += 50
            recommendations.append("Consider adding more bullet points")
        else:
            score += 70

        # Analyze bullet content
        bullet_texts = [b.get("value", "") for b in bullets if isinstance(b, dict)]

        for i, bullet in enumerate(bullet_texts):
            if len(bullet) < 50:
                issues.append(f"Bullet {i+1} is too short")
            elif len(bullet) > 500:
                issues.append(f"Bullet {i+1} may be too long for readability")

        # Check if bullets start with benefit/feature keywords
        benefit_starters = ["enjoy", "perfect", "features", "includes", "made", "designed", "easy", "great"]
        bullets_with_benefits = sum(
            1 for b in bullet_texts
            if any(b.lower().startswith(starter) for starter in benefit_starters)
        )

        if bullets_with_benefits >= 2:
            score += 20
        else:
            recommendations.append("Start bullet points with benefit-focused language")

        # Check for ALL CAPS in bullets
        if any(b.isupper() for b in bullet_texts):
            issues.append("Some bullets are in all caps")
            recommendations.append("Use mixed case for better readability")
        else:
            score += 10

        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "bullet_count": bullet_count,
        }
