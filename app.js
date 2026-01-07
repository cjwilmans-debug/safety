// Amazon PPC Bulk Upload Generator
// Main Application Logic

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the app
    initializeApp();
});

// Global state
let currentCampaignType = 'sponsored-products';
let generatedData = null;

// Campaign type prefixes for naming
const campaignPrefixes = {
    'sponsored-products': 'SP',
    'sponsored-brands': 'SB',
    'sponsored-brands-video': 'SBV',
    'sponsored-display': 'SD'
};

// Column definitions for each campaign type
const columnDefinitions = {
    'sponsored-products': [
        'Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Campaign Daily Budget',
        'Portfolio ID', 'Campaign Start Date', 'Campaign End Date', 'Campaign Targeting Type',
        'Ad Group', 'Max Bid', 'Keyword', 'Product Targeting ID', 'Match Type', 'SKU',
        'Campaign Status', 'Ad Group Status', 'Status', 'Bidding Strategy', 'Placement Type',
        'Bid Adjustment'
    ],
    'sponsored-brands': [
        'Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Budget', 'Budget Type',
        'Portfolio ID', 'Start Date', 'End Date', 'Ad Group', 'Max Bid', 'Keyword',
        'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Landing Page URL',
        'Landing Page Type', 'Brand Name', 'Brand Logo Asset ID', 'Headline', 'ASIN 1',
        'ASIN 2', 'ASIN 3', 'Creative Type'
    ],
    'sponsored-brands-video': [
        'Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Budget', 'Budget Type',
        'Portfolio ID', 'Start Date', 'End Date', 'Ad Group', 'Max Bid', 'Keyword',
        'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'ASIN',
        'Video Asset ID', 'Creative Type'
    ],
    'sponsored-display': [
        'Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Budget', 'Budget Type',
        'Portfolio ID', 'Start Date', 'End Date', 'Tactic', 'Ad Group', 'Max Bid',
        'Campaign Status', 'Ad Group Status', 'Status', 'Targeting', 'ASIN', 'Cost Type',
        'Bid Optimization'
    ]
};

function initializeApp() {
    // Set default start date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('startDate').value = today;

    // Event Listeners
    setupCampaignTypeButtons();
    setupNamingConventionListeners();
    setupFormListeners();
    setupTemplateListeners();
    setupGenerateButton();

    // Load saved templates
    loadTemplatesFromStorage();

    // Initial preview update
    updateCampaignNamePreview();
}

// Campaign Type Selection
function setupCampaignTypeButtons() {
    const buttons = document.querySelectorAll('.campaign-type-btn');

    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Update active state
            buttons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Update current type
            currentCampaignType = this.dataset.type;

            // Show/hide relevant settings sections
            showRelevantSettings(currentCampaignType);

            // Update campaign name preview
            updateCampaignNamePreview();
        });
    });
}

function showRelevantSettings(type) {
    // Hide all campaign-specific sections
    document.querySelectorAll('.campaign-specific').forEach(section => {
        section.style.display = 'none';
    });

    // Show the relevant section
    const sectionId = type + '-settings';
    const section = document.getElementById(sectionId);
    if (section) {
        section.style.display = 'block';
    }
}

// Naming Convention
function setupNamingConventionListeners() {
    const fields = ['brandName', 'productCategory', 'targetingType', 'namingSeparator'];
    fields.forEach(field => {
        document.getElementById(field).addEventListener('input', updateCampaignNamePreview);
        document.getElementById(field).addEventListener('change', updateCampaignNamePreview);
    });
}

function updateCampaignNamePreview() {
    const brandName = document.getElementById('brandName').value || 'Brand';
    const productCategory = document.getElementById('productCategory').value || 'Category';
    const targetingType = document.getElementById('targetingType').value;
    const separator = document.getElementById('namingSeparator').value;

    const prefix = campaignPrefixes[currentCampaignType];
    const campaignName = [prefix, brandName, productCategory, targetingType]
        .filter(part => part)
        .join(separator);

    document.getElementById('campaignNamePreview').textContent = campaignName;
}

function generateCampaignName() {
    const brandName = document.getElementById('brandName').value || 'Brand';
    const productCategory = document.getElementById('productCategory').value || 'Category';
    const targetingType = document.getElementById('targetingType').value;
    const separator = document.getElementById('namingSeparator').value;

    const prefix = campaignPrefixes[currentCampaignType];
    return [prefix, brandName, productCategory, targetingType]
        .filter(part => part)
        .join(separator);
}

function generateAdGroupName() {
    const campaignName = generateCampaignName();
    const adGroupSuffix = document.getElementById('adGroupName').value || 'Main';
    const separator = document.getElementById('namingSeparator').value;
    return campaignName + separator + adGroupSuffix;
}

// Form Listeners
function setupFormListeners() {
    // SP Targeting Type change
    document.getElementById('spTargetingType').addEventListener('change', function() {
        const keywordsSection = document.getElementById('keywordsSection');
        keywordsSection.style.display = this.value === 'manual' ? 'block' : 'none';
    });

    // SD Targeting Type change
    document.getElementById('sdTargetingType').addEventListener('change', function() {
        document.getElementById('sdAudienceSection').style.display =
            this.value === 'audiences' ? 'block' : 'none';
        document.getElementById('sdProductTargetSection').style.display =
            this.value === 'contextual' ? 'block' : 'none';
    });

    // Headline character count
    document.getElementById('sbHeadline').addEventListener('input', function() {
        document.getElementById('headlineCount').textContent = this.value.length;
    });
}

// Template Management
function setupTemplateListeners() {
    document.getElementById('saveTemplate').addEventListener('click', saveTemplate);
    document.getElementById('loadTemplate').addEventListener('change', loadTemplate);
    document.getElementById('deleteTemplate').addEventListener('click', deleteTemplate);
}

function saveTemplate() {
    const name = prompt('Enter a name for this template:');
    if (!name) return;

    const template = {
        campaignType: currentCampaignType,
        brandName: document.getElementById('brandName').value,
        productCategory: document.getElementById('productCategory').value,
        targetingType: document.getElementById('targetingType').value,
        namingSeparator: document.getElementById('namingSeparator').value,
        dailyBudget: document.getElementById('dailyBudget').value,
        campaignStatus: document.getElementById('campaignStatus').value,
        biddingStrategy: document.getElementById('biddingStrategy').value,
        portfolioId: document.getElementById('portfolioId').value,
        adGroupName: document.getElementById('adGroupName').value,
        defaultBid: document.getElementById('defaultBid').value,
        adGroupStatus: document.getElementById('adGroupStatus').value,
        // SP specific
        spTargetingType: document.getElementById('spTargetingType').value,
        // SB specific
        sbLandingPageType: document.getElementById('sbLandingPageType').value,
        sbStorePageUrl: document.getElementById('sbStorePageUrl').value,
        sbHeadline: document.getElementById('sbHeadline').value,
        // SD specific
        sdTargetingType: document.getElementById('sdTargetingType').value,
        sdCostType: document.getElementById('sdCostType').value
    };

    let templates = JSON.parse(localStorage.getItem('ppcTemplates') || '{}');
    templates[name] = template;
    localStorage.setItem('ppcTemplates', JSON.stringify(templates));

    loadTemplatesFromStorage();
    showToast('Template saved!', 'success');
}

function loadTemplate(e) {
    const name = e.target.value;
    if (!name) return;

    const templates = JSON.parse(localStorage.getItem('ppcTemplates') || '{}');
    const template = templates[name];
    if (!template) return;

    // Set campaign type
    document.querySelectorAll('.campaign-type-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.type === template.campaignType) {
            btn.classList.add('active');
        }
    });
    currentCampaignType = template.campaignType;
    showRelevantSettings(template.campaignType);

    // Set form values
    Object.keys(template).forEach(key => {
        const element = document.getElementById(key);
        if (element && key !== 'campaignType') {
            element.value = template[key];
        }
    });

    updateCampaignNamePreview();
    showToast('Template loaded!', 'success');
}

function deleteTemplate() {
    const select = document.getElementById('loadTemplate');
    const name = select.value;
    if (!name) {
        showToast('Please select a template to delete', 'error');
        return;
    }

    if (!confirm(`Delete template "${name}"?`)) return;

    let templates = JSON.parse(localStorage.getItem('ppcTemplates') || '{}');
    delete templates[name];
    localStorage.setItem('ppcTemplates', JSON.stringify(templates));

    loadTemplatesFromStorage();
    showToast('Template deleted', 'success');
}

function loadTemplatesFromStorage() {
    const select = document.getElementById('loadTemplate');
    const templates = JSON.parse(localStorage.getItem('ppcTemplates') || '{}');

    // Clear existing options except the first one
    select.innerHTML = '<option value="">-- Load Template --</option>';

    Object.keys(templates).forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
    });
}

// Generate Button
function setupGenerateButton() {
    document.getElementById('generateBtn').addEventListener('click', generateBulkFile);
    document.getElementById('downloadBtn').addEventListener('click', downloadFile);
}

function generateBulkFile() {
    const campaignName = generateCampaignName();
    const adGroupName = generateAdGroupName();

    let data = [];

    switch (currentCampaignType) {
        case 'sponsored-products':
            data = generateSponsoredProductsData(campaignName, adGroupName);
            break;
        case 'sponsored-brands':
            data = generateSponsoredBrandsData(campaignName, adGroupName);
            break;
        case 'sponsored-brands-video':
            data = generateSponsoredBrandsVideoData(campaignName, adGroupName);
            break;
        case 'sponsored-display':
            data = generateSponsoredDisplayData(campaignName, adGroupName);
            break;
    }

    if (data.length === 0) {
        showToast('Please fill in the required fields', 'error');
        return;
    }

    generatedData = data;
    displayPreview(data);
    showToast('Bulk file generated!', 'success');
}

// Sponsored Products Generation
function generateSponsoredProductsData(campaignName, adGroupName) {
    const data = [];
    const columns = columnDefinitions['sponsored-products'];

    const dailyBudget = document.getElementById('dailyBudget').value;
    const startDate = formatDate(document.getElementById('startDate').value);
    const endDate = formatDate(document.getElementById('endDate').value);
    const campaignStatus = document.getElementById('campaignStatus').value;
    const biddingStrategy = document.getElementById('biddingStrategy').value;
    const portfolioId = document.getElementById('portfolioId').value;
    const defaultBid = document.getElementById('defaultBid').value;
    const adGroupStatus = document.getElementById('adGroupStatus').value;
    const targetingType = document.getElementById('spTargetingType').value;

    const skus = document.getElementById('skuList').value
        .split('\n')
        .map(s => s.trim())
        .filter(s => s);

    if (skus.length === 0) {
        return [];
    }

    // Campaign row
    const campaignRow = createEmptyRow(columns);
    campaignRow['Record Type'] = 'Campaign';
    campaignRow['Campaign'] = campaignName;
    campaignRow['Campaign Daily Budget'] = dailyBudget;
    campaignRow['Portfolio ID'] = portfolioId;
    campaignRow['Campaign Start Date'] = startDate;
    campaignRow['Campaign End Date'] = endDate;
    campaignRow['Campaign Targeting Type'] = targetingType === 'auto' ? 'Auto' : 'Manual';
    campaignRow['Campaign Status'] = campaignStatus;
    campaignRow['Bidding Strategy'] = biddingStrategy;
    data.push(campaignRow);

    // Ad Group row
    const adGroupRow = createEmptyRow(columns);
    adGroupRow['Record Type'] = 'Ad Group';
    adGroupRow['Campaign'] = campaignName;
    adGroupRow['Ad Group'] = adGroupName;
    adGroupRow['Max Bid'] = defaultBid;
    adGroupRow['Ad Group Status'] = adGroupStatus;
    data.push(adGroupRow);

    // Product Ad rows for each SKU
    skus.forEach(sku => {
        const productRow = createEmptyRow(columns);
        productRow['Record Type'] = 'Product Ad';
        productRow['Campaign'] = campaignName;
        productRow['Ad Group'] = adGroupName;
        productRow['SKU'] = sku;
        productRow['Status'] = 'enabled';
        data.push(productRow);
    });

    // Keywords (for manual targeting)
    if (targetingType === 'manual') {
        const keywords = document.getElementById('keywordList').value
            .split('\n')
            .map(k => k.trim())
            .filter(k => k);

        keywords.forEach(keywordLine => {
            const parts = keywordLine.split(',').map(p => p.trim());
            const keyword = parts[0];
            const matchType = parts[1] || 'broad';
            const bid = parts[2] || defaultBid;

            const keywordRow = createEmptyRow(columns);
            keywordRow['Record Type'] = 'Keyword';
            keywordRow['Campaign'] = campaignName;
            keywordRow['Ad Group'] = adGroupName;
            keywordRow['Keyword'] = keyword;
            keywordRow['Match Type'] = matchType;
            keywordRow['Max Bid'] = bid;
            keywordRow['Status'] = 'enabled';
            data.push(keywordRow);
        });
    }

    return data;
}

// Sponsored Brands Generation
function generateSponsoredBrandsData(campaignName, adGroupName) {
    const data = [];
    const columns = columnDefinitions['sponsored-brands'];

    const dailyBudget = document.getElementById('dailyBudget').value;
    const startDate = formatDate(document.getElementById('startDate').value);
    const endDate = formatDate(document.getElementById('endDate').value);
    const campaignStatus = document.getElementById('campaignStatus').value;
    const portfolioId = document.getElementById('portfolioId').value;
    const defaultBid = document.getElementById('defaultBid').value;
    const adGroupStatus = document.getElementById('adGroupStatus').value;

    const landingPageType = document.getElementById('sbLandingPageType').value;
    const storePageUrl = document.getElementById('sbStorePageUrl').value;
    const headline = document.getElementById('sbHeadline').value;

    const asins = document.getElementById('sbAsins').value
        .split('\n')
        .map(a => a.trim())
        .filter(a => a);

    const keywords = document.getElementById('sbKeywords').value
        .split('\n')
        .map(k => k.trim())
        .filter(k => k);

    if (asins.length < 3) {
        showToast('Sponsored Brands requires at least 3 ASINs', 'error');
        return [];
    }

    // Campaign row
    const campaignRow = createEmptyRow(columns);
    campaignRow['Record Type'] = 'Campaign';
    campaignRow['Campaign'] = campaignName;
    campaignRow['Budget'] = dailyBudget;
    campaignRow['Budget Type'] = 'daily';
    campaignRow['Portfolio ID'] = portfolioId;
    campaignRow['Start Date'] = startDate;
    campaignRow['End Date'] = endDate;
    campaignRow['Campaign Status'] = campaignStatus;
    data.push(campaignRow);

    // Ad Group row
    const adGroupRow = createEmptyRow(columns);
    adGroupRow['Record Type'] = 'Ad Group';
    adGroupRow['Campaign'] = campaignName;
    adGroupRow['Ad Group'] = adGroupName;
    adGroupRow['Ad Group Status'] = adGroupStatus;
    data.push(adGroupRow);

    // Ad row with creative
    const adRow = createEmptyRow(columns);
    adRow['Record Type'] = 'Ad';
    adRow['Campaign'] = campaignName;
    adRow['Ad Group'] = adGroupName;
    adRow['Landing Page URL'] = storePageUrl;
    adRow['Landing Page Type'] = landingPageType;
    adRow['Headline'] = headline;
    adRow['ASIN 1'] = asins[0] || '';
    adRow['ASIN 2'] = asins[1] || '';
    adRow['ASIN 3'] = asins[2] || '';
    adRow['Creative Type'] = 'productCollection';
    adRow['Status'] = 'enabled';
    data.push(adRow);

    // Keywords
    keywords.forEach(keywordLine => {
        const parts = keywordLine.split(',').map(p => p.trim());
        const keyword = parts[0];
        const matchType = parts[1] || 'broad';
        const bid = parts[2] || defaultBid;

        const keywordRow = createEmptyRow(columns);
        keywordRow['Record Type'] = 'Keyword';
        keywordRow['Campaign'] = campaignName;
        keywordRow['Ad Group'] = adGroupName;
        keywordRow['Keyword'] = keyword;
        keywordRow['Match Type'] = matchType;
        keywordRow['Max Bid'] = bid;
        keywordRow['Status'] = 'enabled';
        data.push(keywordRow);
    });

    return data;
}

// Sponsored Brands Video Generation
function generateSponsoredBrandsVideoData(campaignName, adGroupName) {
    const data = [];
    const columns = columnDefinitions['sponsored-brands-video'];

    const dailyBudget = document.getElementById('dailyBudget').value;
    const startDate = formatDate(document.getElementById('startDate').value);
    const endDate = formatDate(document.getElementById('endDate').value);
    const campaignStatus = document.getElementById('campaignStatus').value;
    const portfolioId = document.getElementById('portfolioId').value;
    const defaultBid = document.getElementById('defaultBid').value;
    const adGroupStatus = document.getElementById('adGroupStatus').value;

    const asin = document.getElementById('sbvAsin').value.trim();
    const videoAssetId = document.getElementById('sbvVideoAssetId').value.trim();

    const keywords = document.getElementById('sbvKeywords').value
        .split('\n')
        .map(k => k.trim())
        .filter(k => k);

    if (!asin) {
        showToast('Please enter a product ASIN', 'error');
        return [];
    }

    // Campaign row
    const campaignRow = createEmptyRow(columns);
    campaignRow['Record Type'] = 'Campaign';
    campaignRow['Campaign'] = campaignName;
    campaignRow['Budget'] = dailyBudget;
    campaignRow['Budget Type'] = 'daily';
    campaignRow['Portfolio ID'] = portfolioId;
    campaignRow['Start Date'] = startDate;
    campaignRow['End Date'] = endDate;
    campaignRow['Campaign Status'] = campaignStatus;
    data.push(campaignRow);

    // Ad Group row
    const adGroupRow = createEmptyRow(columns);
    adGroupRow['Record Type'] = 'Ad Group';
    adGroupRow['Campaign'] = campaignName;
    adGroupRow['Ad Group'] = adGroupName;
    adGroupRow['Ad Group Status'] = adGroupStatus;
    data.push(adGroupRow);

    // Video Ad row
    const adRow = createEmptyRow(columns);
    adRow['Record Type'] = 'Ad';
    adRow['Campaign'] = campaignName;
    adRow['Ad Group'] = adGroupName;
    adRow['ASIN'] = asin;
    adRow['Video Asset ID'] = videoAssetId;
    adRow['Creative Type'] = 'video';
    adRow['Status'] = 'enabled';
    data.push(adRow);

    // Keywords
    keywords.forEach(keywordLine => {
        const parts = keywordLine.split(',').map(p => p.trim());
        const keyword = parts[0];
        const matchType = parts[1] || 'broad';
        const bid = parts[2] || defaultBid;

        const keywordRow = createEmptyRow(columns);
        keywordRow['Record Type'] = 'Keyword';
        keywordRow['Campaign'] = campaignName;
        keywordRow['Ad Group'] = adGroupName;
        keywordRow['Keyword'] = keyword;
        keywordRow['Match Type'] = matchType;
        keywordRow['Max Bid'] = bid;
        keywordRow['Status'] = 'enabled';
        data.push(keywordRow);
    });

    return data;
}

// Sponsored Display Generation
function generateSponsoredDisplayData(campaignName, adGroupName) {
    const data = [];
    const columns = columnDefinitions['sponsored-display'];

    const dailyBudget = document.getElementById('dailyBudget').value;
    const startDate = formatDate(document.getElementById('startDate').value);
    const endDate = formatDate(document.getElementById('endDate').value);
    const campaignStatus = document.getElementById('campaignStatus').value;
    const portfolioId = document.getElementById('portfolioId').value;
    const defaultBid = document.getElementById('defaultBid').value;
    const adGroupStatus = document.getElementById('adGroupStatus').value;

    const targetingType = document.getElementById('sdTargetingType').value;
    const costType = document.getElementById('sdCostType').value;

    const asins = document.getElementById('sdAsins').value
        .split('\n')
        .map(a => a.trim())
        .filter(a => a);

    if (asins.length === 0) {
        showToast('Please enter at least one ASIN', 'error');
        return [];
    }

    // Determine tactic based on targeting type
    const tactic = targetingType === 'audiences' ? 'T00030' : 'T00020'; // Audiences vs Contextual

    // Campaign row
    const campaignRow = createEmptyRow(columns);
    campaignRow['Record Type'] = 'Campaign';
    campaignRow['Campaign'] = campaignName;
    campaignRow['Budget'] = dailyBudget;
    campaignRow['Budget Type'] = 'daily';
    campaignRow['Portfolio ID'] = portfolioId;
    campaignRow['Start Date'] = startDate;
    campaignRow['End Date'] = endDate;
    campaignRow['Tactic'] = tactic;
    campaignRow['Campaign Status'] = campaignStatus;
    data.push(campaignRow);

    // Ad Group row
    const adGroupRow = createEmptyRow(columns);
    adGroupRow['Record Type'] = 'Ad Group';
    adGroupRow['Campaign'] = campaignName;
    adGroupRow['Ad Group'] = adGroupName;
    adGroupRow['Max Bid'] = defaultBid;
    adGroupRow['Ad Group Status'] = adGroupStatus;
    adGroupRow['Cost Type'] = costType;
    adGroupRow['Bid Optimization'] = 'reach';
    data.push(adGroupRow);

    // Product Ad rows for each ASIN
    asins.forEach(asin => {
        const productRow = createEmptyRow(columns);
        productRow['Record Type'] = 'Product Ad';
        productRow['Campaign'] = campaignName;
        productRow['Ad Group'] = adGroupName;
        productRow['ASIN'] = asin;
        productRow['Status'] = 'enabled';
        data.push(productRow);
    });

    // Targeting rows
    if (targetingType === 'audiences') {
        const audiences = document.getElementById('sdAudiences').value
            .split('\n')
            .map(a => a.trim())
            .filter(a => a);

        audiences.forEach(audience => {
            const targetRow = createEmptyRow(columns);
            targetRow['Record Type'] = 'Targeting';
            targetRow['Campaign'] = campaignName;
            targetRow['Ad Group'] = adGroupName;
            targetRow['Targeting'] = audience;
            targetRow['Status'] = 'enabled';
            data.push(targetRow);
        });
    } else {
        const targets = document.getElementById('sdProductTargets').value
            .split('\n')
            .map(t => t.trim())
            .filter(t => t);

        targets.forEach(target => {
            const targetRow = createEmptyRow(columns);
            targetRow['Record Type'] = 'Targeting';
            targetRow['Campaign'] = campaignName;
            targetRow['Ad Group'] = adGroupName;
            targetRow['Targeting'] = target;
            targetRow['Status'] = 'enabled';
            data.push(targetRow);
        });
    }

    return data;
}

// Helper Functions
function createEmptyRow(columns) {
    const row = {};
    columns.forEach(col => row[col] = '');
    return row;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
}

function displayPreview(data) {
    const previewSection = document.getElementById('previewSection');
    const thead = document.querySelector('#previewTable thead');
    const tbody = document.querySelector('#previewTable tbody');

    if (data.length === 0) {
        previewSection.style.display = 'none';
        return;
    }

    const columns = Object.keys(data[0]);

    // Build header
    thead.innerHTML = '<tr>' + columns.map(col => `<th>${col}</th>`).join('') + '</tr>';

    // Build body
    tbody.innerHTML = data.map(row =>
        '<tr>' + columns.map(col => `<td>${row[col] || ''}</td>`).join('') + '</tr>'
    ).join('');

    previewSection.style.display = 'block';
    previewSection.scrollIntoView({ behavior: 'smooth' });
}

function downloadFile() {
    if (!generatedData || generatedData.length === 0) {
        showToast('No data to download', 'error');
        return;
    }

    const format = document.querySelector('input[name="exportFormat"]:checked').value;
    const campaignName = generateCampaignName().replace(/[^a-zA-Z0-9]/g, '_');
    const filename = `${campaignName}_bulk_upload`;

    if (format === 'csv') {
        downloadCSV(filename);
    } else {
        downloadExcel(filename);
    }
}

function downloadCSV(filename) {
    const columns = Object.keys(generatedData[0]);

    let csv = columns.join(',') + '\n';

    generatedData.forEach(row => {
        csv += columns.map(col => {
            let val = row[col] || '';
            // Escape quotes and wrap in quotes if contains comma
            if (val.toString().includes(',') || val.toString().includes('"')) {
                val = '"' + val.toString().replace(/"/g, '""') + '"';
            }
            return val;
        }).join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename + '.csv';
    link.click();

    showToast('CSV downloaded!', 'success');
}

function downloadExcel(filename) {
    const columns = Object.keys(generatedData[0]);

    // Convert data to array of arrays
    const wsData = [columns];
    generatedData.forEach(row => {
        wsData.push(columns.map(col => row[col] || ''));
    });

    // Create workbook and worksheet
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(wsData);

    // Set column widths
    const colWidths = columns.map(col => ({ wch: Math.max(col.length, 15) }));
    ws['!cols'] = colWidths;

    XLSX.utils.book_append_sheet(wb, ws, 'Bulk Upload');
    XLSX.writeFile(wb, filename + '.xlsx');

    showToast('Excel file downloaded!', 'success');
}

// Toast Notifications
function showToast(message, type = 'info') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
