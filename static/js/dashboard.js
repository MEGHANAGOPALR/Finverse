// static/js/dashboard.js

import { getUserId, getAbsoluteUrl, apiFetch } from './utils.js';

let expenseChart = null; // Variable for Category Distribution (Pie Chart)
let monthlySummaryChart = null; // Variable for Monthly Spending (Bar Chart)
let topTransactionsChart = null; // Variable for Top Transactions (Horizontal Bar)
let categoryTrendsChart = null; // Variable for Category Trends (Stacked Bar/Line)

// --- Utility Functions ---

/**
 * Ensures the user is logged in before allowing access to the dashboard.
 */
function checkAuthentication() {
    const userId = getUserId();
    if (!userId) {
        alert('You must be logged in to view the dashboard.');
        window.location.href = getAbsoluteUrl('/login');
        return null;
    }
    return userId;
}

/**
 * Formats a number as currency (Rupees).
 * @param {number} amount
 * @returns {string} Formatted currency string.
 */
function formatCurrency(amount) {
    // Using Indian Rupee (₹) symbol and locale for formatting
    if (typeof amount !== 'number') return '₹0.00';
    return '₹' + amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Converts simple Markdown (headers, tables, bold, numbered lists) to HTML.
 * NOTE: This is a basic implementation and will not handle complex Markdown.
 * @param {string} markdown - The markdown string.
 * @returns {string} The HTML string.
 */
function markdownToHtml(markdown) {
    // 1. Convert Headers
    let html = markdown.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    
    // 2. Convert Bold/Strong
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // 3. Convert Numbered Lists (needs careful handling for newline separation)
    html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');
    
    // Wrap list items in <ol> tags
    if (html.includes('<li>')) {
        // Simple logic to wrap list items generated above
        html = html.replace(/(<li>.*<\/li>)/s, '<ol class="analysis-list">$1</ol>');
    }

    // 4. Preserve newlines for pre-formatted sections like tables and lists
    html = html.replace(/\n\n/g, '<p></p>'); // Separate paragraphs
    html = html.replace(/\n/g, '<br>');      // Convert remaining single newlines to <br> for spacing

    // Final clean up for list/table rendering
    html = html.replace(/<br><h2>/g, '<h2>');
    html = html.replace(/<\/h2><br>/g, '</h2>');
    html = html.replace(/<br><li>/g, '<li>');
    
    return html;
}

// --- Chart Functions ---

// Define a professional color palette for consistency
const CHART_COLORS = [
    '#059669', // Emerald Green (Primary)
    '#34d399', 
    '#065f46',
    '#facc15', // Yellow
    '#f87171', // Red
    '#60a5fa', // Blue
    '#818cf8', // Indigo
    '#a78bfa', // Violet
    '#d946ef', // Fuchsia
    '#fb923c', // Orange
    '#ef4444', // Fallback Red
    '#1f2937', // Fallback Dark
];

// Reusable function to get a color based on index
function getColor(index) {
    return CHART_COLORS[index % CHART_COLORS.length];
}

/**
 * Processes category data: sorts, limits top categories, and groups the rest into "Other".
 * @param {Array<object>} categories - List of {category, percent} objects.
 * @param {number} limit - Maximum number of categories to display (excluding 'Other').
 * @returns {object} {labels, dataPoints}
 */
function processCategoryDistributionData(categories, limit = 8) {
    if (categories.length === 0) {
        return { labels: ['No Data'], dataPoints: [100] };
    }

    // Sort by percentage descending
    categories.sort((a, b) => b.percent - a.percent);

    const topCategories = categories.slice(0, limit);
    const otherCategories = categories.slice(limit);

    let labels = topCategories.map(c => c.category);
    let dataPoints = topCategories.map(c => c.percent);
    let colors = topCategories.map((_, i) => getColor(i));

    if (otherCategories.length > 0) {
        const otherPercent = otherCategories.reduce((sum, c) => sum + c.percent, 0);
        labels.push('Other');
        dataPoints.push(otherPercent);
        colors.push('#9ca3af'); // Grey for 'Other'
    }
    
    return { labels, dataPoints, colors };
}

/**
 * Renders Chart B: Category-wise Spending Distribution (Doughnut Chart)
 * @param {Array<object>} categories - List of {category, percent} objects.
 */
export function renderCategoryDistributionChart(categories) {
    const ctx = document.getElementById('category-distribution-chart');
    if (!ctx) return;

    // Use the new processing function to limit categories
    const processedData = processCategoryDistributionData(categories, 8); // Display top 8 categories + 'Other'

    const data = {
        labels: processedData.labels,
        datasets: [{
            data: processedData.dataPoints,
            backgroundColor: processedData.colors,
            hoverOffset: 4,
            borderWidth: 1, 
        }]
    };

    const config = {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right', 
                    labels: {
                        font: { family: 'Arial, sans-serif' }
                    }
                },
                title: {
                    display: true,
                    text: 'Category-wise Spending Distribution (%)',
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (context.parsed !== null) {
                                label += ': ' + context.parsed.toFixed(1) + '%';
                            }
                            return label;
                        }
                    }
                }
            },
            cutout: '70%', 
        }
    };

    if (expenseChart) {
        expenseChart.destroy();
    }
    expenseChart = new Chart(ctx, config);
}


/**
 * Renders Chart C: Monthly Spending Summary (Bar Chart)
 * @param {Array<object>} monthlySummary - List of {month, total_amount} objects.
 */
export function renderMonthlySummaryChart(monthlySummary) {
    const ctx = document.getElementById('monthly-spending-chart');
    if (!ctx) return;

    // Sort the data by month (YYYY-MM)
    monthlySummary.sort((a, b) => a.month.localeCompare(b.month));

    const labels = monthlySummary.map(d => {
        // Convert YYYY-MM to Month YYYY (e.g., "05-2025" -> "May 2025")
        const [year, month] = d.month.split('-');
        return new Date(year, month - 1).toLocaleString('en-US', { month: 'short', year: '2-digit' });
    });
    const dataPoints = monthlySummary.map(d => d.total_amount);

    const data = {
        labels: labels,
        datasets: [{
            label: 'Total Spending (₹)',
            data: dataPoints,
            backgroundColor: getColor(0),
            borderColor: getColor(0),
            borderWidth: 1
        }]
    };

    const config = {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Monthly Spending Summary (₹)',
                    font: { size: 16 }
                },
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (context.parsed.y !== null) {
                                label += ': ' + formatCurrency(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Amount (₹)'
                    }
                }
            }
        }
    };

    if (monthlySummaryChart) {
        monthlySummaryChart.destroy();
    }
    monthlySummaryChart = new Chart(ctx, config);
}


/**
 * Renders Chart D: Top 5 Highest Transactions (Horizontal Bar Chart)
 * @param {Array<object>} topTransactions - List of {description, amount, category} objects.
 */
export function renderTopTransactionsChart(topTransactions) {
    const ctx = document.getElementById('top-transactions-chart');
    if (!ctx) return;

    // Data for horizontal bar chart is usually shown high-to-low
    topTransactions.sort((a, b) => b.amount - a.amount);

    const labels = topTransactions.map(d => `${d.description.substring(0, 20)}... (${d.category})`);
    const dataPoints = topTransactions.map(d => d.amount);

    const data = {
        labels: labels,
        datasets: [{
            label: 'Transaction Amount (₹)',
            data: dataPoints,
            backgroundColor: getColor(3),
            borderColor: getColor(3),
            borderWidth: 1
        }]
    };

    const config = {
        type: 'bar',
        data: data,
        options: {
            indexAxis: 'y', // Make it a horizontal bar chart
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Top 5 Highest Transactions (₹)',
                    font: { size: 16 }
                },
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (context.parsed.x !== null) {
                                label += ': ' + formatCurrency(context.parsed.x);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Amount (₹)'
                    }
                }
            }
        }
    };

    if (topTransactionsChart) {
        topTransactionsChart.destroy();
    }
    topTransactionsChart = new Chart(ctx, config);
}


/**
 * Renders Chart A/E: Category Trends Over Time (Line Chart for simplicity)
 * @param {Array<object>} categoryTrends - List of {month, category, amount} objects.
 */
export function renderCategoryTrendsChart(categoryTrends) {
    const ctx = document.getElementById('category-trends-chart');
    if (!ctx) return;
    
    // Grouping the data for Chart.js
    const dataMap = categoryTrends.reduce((acc, curr) => {
        acc.months.add(curr.month);
        acc.categories.add(curr.category);
        acc.data[curr.month] = acc.data[curr.month] || {};
        acc.data[curr.month][curr.category] = curr.amount;
        return acc;
    }, { months: new Set(), categories: new Set(), data: {} });
    
    const months = Array.from(dataMap.months).sort();
    const categories = Array.from(dataMap.categories);

    // Create datasets
    const datasets = categories.map((category, index) => {
        const data = months.map(month => dataMap.data[month][category] || 0);
        return {
            label: category,
            data: data,
            backgroundColor: getColor(index),
            borderColor: getColor(index),
            fill: false,
            tension: 0.1, // Smooth lines
        };
    });

    const labels = months.map(d => {
        const [year, month] = d.split('-');
        return new Date(year, month - 1).toLocaleString('en-US', { month: 'short', year: '2-digit' });
    });

    const data = {
        labels: labels,
        datasets: datasets
    };

    const config = {
        type: 'line', // Line chart for trend visualization
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Category Trends Over Time (₹)',
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (context.parsed.y !== null) {
                                label += ': ' + formatCurrency(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Month' }
                },
                y: {
                    stacked: false, // Not stacked for clean trend lines
                    title: { display: true, text: 'Amount (₹)' }
                }
            }
        }
    };

    if (categoryTrendsChart) {
        categoryTrendsChart.destroy();
    }
    categoryTrendsChart = new Chart(ctx, config);
}


// --- API Handlers ---

/**
 * Requests and displays the AI financial analysis and all charts.
 */
export async function generateAnalysis() {
    const userId = getUserId();
    if (!userId) return;

    const analysisButton = document.getElementById('generate-analysis-button');
    const analysisSummaryDiv = document.getElementById('analysis-summary');
    const analysisCard = document.querySelector('.analysis-results-card');

    analysisButton.disabled = true;
    analysisButton.textContent = 'Generating...';
    analysisSummaryDiv.innerHTML = '<p class="text-center">Analyzing transactions. Please wait...</p>';
    analysisCard.style.display = 'flex'; // Show the main results card

    try {
        const response = await apiFetch(getAbsoluteUrl(`/api/generate_analysis/${userId}`), 'POST', { user_id: userId });

        if (response.success) {
            const chartData = response.charts || {};
            
            // 1. Render Analysis Summary using the Markdown converter
            const htmlContent = markdownToHtml(response.summary);
            analysisSummaryDiv.innerHTML = htmlContent;

            // 2. Render all Charts
            renderCategoryDistributionChart(chartData.category_distribution || []); // Chart B (Doughnut)
            renderMonthlySummaryChart(chartData.monthly_summary || []);           // Chart C (Bar)
            renderTopTransactionsChart(chartData.top_transactions || []);         // Chart D (Horizontal Bar)
            renderCategoryTrendsChart(chartData.category_trends || []);           // Chart A/E (Line)

            // Show chart container
            document.getElementById('chart-grid').style.display = 'grid';
            
        } else {
            analysisSummaryDiv.innerHTML = `<p class="text-red-500">Analysis failed: ${response.message || 'Server error.'}</p>`;
            document.getElementById('chart-grid').style.display = 'none';
        }

    } catch (error) {
        console.error("Analysis generation failed:", error);
        analysisSummaryDiv.innerHTML = `<p class="text-red-500">Network error: ${error.message}</p>`;
        document.getElementById('chart-grid').style.display = 'none';
    } finally {
        analysisButton.disabled = false;
        analysisButton.textContent = 'Generate Financial Analysis';
    }
}


/**
 * Handles the click event for the CSV upload button.
 */
export async function handleCSVUpload() {
    const userId = getUserId();
    if (!userId) return;

    const fileInput = document.getElementById('csv-file-input');
    const uploadButton = document.getElementById('upload-csv-button');
    const uploadStatus = document.getElementById('upload-status');
    const file = fileInput.files[0];

    if (!file) {
        uploadStatus.innerHTML = '<span style="color: var(--error-color);">Please select a CSV file.</span>';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    uploadButton.disabled = true;
    uploadButton.textContent = 'Uploading...';
    uploadStatus.innerHTML = '';

    try {
        // Use standard fetch here because apiFetch defaults to JSON content type,
        // which conflicts with FormData/multipart upload
        const response = await fetch(getAbsoluteUrl(`/api/upload_transactions/${userId}`), {
            method: 'POST',
            body: formData // The body is the FormData object
        });
        
        const data = await response.json();

        if (response.ok && data.success) {
            uploadStatus.innerHTML = `<span style="color: var(--primary-color);">✅ Success! ${data.count} records loaded. Now, generate your analysis.</span>`;
            // Suggest running analysis after successful upload
            document.getElementById('generate-analysis-button').scrollIntoView({ behavior: 'smooth' });
            
        } else {
            // Handle server-side errors (e.g., CSV format error)
            uploadStatus.innerHTML = `<span style="color: var(--error-color);">❌ Upload failed: ${data.message || 'Server error.'}</span>`;
        }

    } catch (error) {
        console.error("Upload failed:", error);
        uploadStatus.innerHTML = `<span style="color: var(--error-color);">Network error: ${error.message}</span>`;
    } finally {
        uploadButton.disabled = false;
        uploadButton.textContent = 'Upload Transactions';
    }
}


/**
 * Loads and displays the user's KPI data (not implemented in this turn, kept for structure)
 */
export async function loadDashboardData(userId) {
    // Placeholder function for loading initial KPIs/profile data
    console.log(`Dashboard initializing for user: ${userId}`);
}


// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    const userId = checkAuthentication();
    if (userId) {
        loadDashboardData(userId);
        
        // Attach Event Listeners
        document.getElementById('upload-csv-button').addEventListener('click', handleCSVUpload);
        document.getElementById('generate-analysis-button').addEventListener('click', generateAnalysis);
    }
});