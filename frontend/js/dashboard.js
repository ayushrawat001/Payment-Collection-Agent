
// ========================================
// API CONFIGURATION
// ========================================

const API_BASE_URL =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "https://payment-collection-agent.onrender.com";


// ========================================
// GLOBAL CUSTOMER DATA
// ========================================

// Stores the customer records received from FastAPI.
// Search and filters will work on this array.

let allCustomers = [];
let selectedProduct = "";


// INR currency formatter

const currencyFormatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
});


// ========================================
// FETCH ALL CUSTOMERS
// ========================================

async function fetchCustomers() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/customers`
        );

        if (!response.ok) {
            throw new Error("Unable to fetch customers");
        }

        const data = await response.json();

        return data.customers;

    } catch (error) {

        console.error("Customer API Error:", error);

        throw error;
    }
}

// Current date

const d = new Date();

const day = d.toLocaleDateString("en-IN", { weekday: "long" }); 
const date = d.getDate();                                      
const month = d.toLocaleDateString("en-IN", { month: "long" }); 

const formattedDate = `${day}, ${date} ${month}`.toUpperCase();

document.getElementsByClassName("hero-date")[0].textContent = formattedDate;


// ========================================
// CALCULATE STATISTICS
// ========================================

function calculateStatistics(customers) {

    const totalOutstanding = customers.reduce(
        (total, customer) =>
            total + (Number(customer.outstanding) || 0),
        0
    );

    const totalOverdue = customers.reduce(
        (total, customer) =>
            total + (Number(customer.overdue_amt) || 0),
        0
    );

    const totalCustomers = customers.length;

    const overdueCustomers = customers.filter(
        customer =>
            customer.overdue === true ||
            String(customer.overdue).toLowerCase() === "true"
    ).length;

    return {
        totalOutstanding,
        totalOverdue,
        totalCustomers,
        overdueCustomers
    };
}


// ========================================
// DISPLAY STATISTICS
// ========================================

function displayStatistics(stats) {

    document.getElementById("totalOutstanding").textContent =
        currencyFormatter.format(stats.totalOutstanding);

    document.getElementById("totalOverdue").textContent =
        currencyFormatter.format(stats.totalOverdue);

    document.getElementById("totalCustomers").textContent =
        stats.totalCustomers;

    document.getElementById("overdueCustomers").textContent =
        stats.overdueCustomers;
}

// ========================================
// RENDER PRODUCT FILTER CHIPS
// ========================================

function renderProductFilters(customers) {

    const container = document.getElementById("productFilters");

    container.replaceChildren();

    // Count customers by loan product
    const productCounts = new Map();

    customers.forEach(customer => {

        const product = String(customer.product || "").trim();

        if (!product) return;

        productCounts.set(
            product,
            (productCounts.get(product) || 0) + 1
        );

    });


    // Helper function to create a filter chip
    function createChip(label, count, productValue) {

        const button = document.createElement("button");

        button.type = "button";

        button.className =
            selectedProduct === productValue
                ? "filter-chip active"
                : "filter-chip";

        button.setAttribute(
            "aria-pressed",
            String(selectedProduct === productValue)
        );


        const labelText = document.createElement("span");
        labelText.textContent = label;

        const countText = document.createElement("span");

        countText.className = "filter-chip-count";
        countText.textContent = count;


        button.append(labelText, countText);


        button.addEventListener("click", () => {

            selectedProduct = productValue;

            renderProductFilters(allCustomers);

            filterCustomers();

        });

        return button;
    }


    // ALL CUSTOMERS CHIP
    container.appendChild(
        createChip("All", customers.length, "")
    );


    // PRODUCT CHIPS
    productCounts.forEach((count, product) => {

        container.appendChild(
            createChip(product, count, product)
        );

    });

}

// Name Initials

function getCustomerInitials(name) {

    const parts = String(name || "")
        .trim()
        .split(/\s+/)
        .filter(Boolean);

    return parts
        .slice(0, 2)
        .map(part => part.charAt(0).toUpperCase())
        .join("") || "?";

}


function createLinkIcon() {

    const icon = document.createElement("i");

    icon.className = "fa-solid fa-link";

    icon.setAttribute("aria-hidden", "true");

    return icon;
}   

// ========================================
// RENDER CUSTOMER TABLE
// ========================================


function renderCustomerTable(customers) {

    const tableBody =
        document.getElementById("customersTableBody");

    const customerCount =
        document.getElementById("customerCount");

    tableBody.replaceChildren();


    // Handle empty search/filter results
    if (customers.length === 0) {

        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 6;
        cell.className = "table-message";
        cell.textContent = "No customers found.";

        row.appendChild(cell);
        tableBody.appendChild(row);

        customerCount.textContent =
            `Showing 0 of ${allCustomers.length} customers`;

        return;
    }


    // Generate each customer row
    customers.forEach(customer => {

        const row = document.createElement("tr");


        // =================================
        // 1. CUSTOMER IDENTITY
        // =================================

        const customerCell = document.createElement("td");

        const identity = document.createElement("div");
        identity.className = "customer-identity";


        // Initials avatar
        const avatar = document.createElement("div");

        avatar.className = "customer-avatar";

        avatar.textContent =
            getCustomerInitials(customer.name);


        // Customer name
        const details = document.createElement("div");

        details.className = "customer-details";


        const name = document.createElement("span");

        name.className = "customer-name";
        name.textContent = customer.name || "Unnamed customer";


        // Customer ID
        const id = document.createElement("small");

        id.className = "customer-id";
        id.textContent = customer.id || "No ID";


        details.append(name, id);

        identity.append(avatar, details);

        customerCell.appendChild(identity);


        // =================================
        // 2. PRODUCT
        // =================================

        const productCell = document.createElement("td");

        productCell.textContent =
            customer.product || "N/A";


        // =================================
        // 3. OUTSTANDING AMOUNT
        // =================================

        const outstanding =
            Number(customer.outstanding) || 0;

        const outstandingCell =
            document.createElement("td");

        outstandingCell.className = "amount-cell";

        outstandingCell.textContent =
            currencyFormatter.format(outstanding);


        // =================================
        // 4. OVERDUE AMOUNT + PERCENTAGE
        // =================================

        const overdue =
            Number(customer.overdue_amt) || 0;

        const overduePercent =
            outstanding > 0
                ? Math.round((overdue / outstanding) * 100)
                : 0;


        const overdueCell =
            document.createElement("td");

        overdueCell.className = "overdue-cell";


        // Amount and percentage row
        const overdueTop =
            document.createElement("div");

        overdueTop.className = "overdue-top";


        const overdueAmount =
            document.createElement("span");

        overdueAmount.className = "overdue-amount";

        overdueAmount.textContent =
            currencyFormatter.format(overdue);


        const percentage =
            document.createElement("span");

        percentage.className = "overdue-percentage";

        percentage.textContent =
            `${overduePercent}% of balance`;


        overdueTop.append(overdueAmount, percentage);


        // Progress bar
        const progress =
            document.createElement("div");

        progress.className = "overdue-progress";


        const progressFill =
            document.createElement("div");

        progressFill.className = "overdue-progress-fill";

        const safePercentage =
            Math.max(0, Math.min(overduePercent, 100));

        progressFill.style.width =
            `${safePercentage}%`;


        progress.appendChild(progressFill);

        overdueCell.append(overdueTop, progress);


        // =================================
        // 5. LAST OUTCOME
        // =================================

        const outcomeCell =
            document.createElement("td");

        const outcomeTag =
            document.createElement("span");

        const outcome =
            customer.last_outcome || "Not called yet";

        outcomeTag.className = "outcome-tag";


        const normalizedOutcome =
            outcome.toLowerCase();


        if (normalizedOutcome.includes("promise")) {

            outcomeTag.classList.add("outcome-promise");

        } else if (normalizedOutcome.includes("callback")) {

            outcomeTag.classList.add("outcome-callback");

        } else if (normalizedOutcome.includes("refused")) {

            outcomeTag.classList.add("outcome-refused");

        }

        outcomeTag.textContent = outcome;

        outcomeCell.appendChild(outcomeTag);


        // =================================
        // 6. ACTION BUTTONS
        // =================================

        const actionCell =
            document.createElement("td");

        const actions =
            document.createElement("div");

        actions.className = "table-actions";


        // Link icon button
        const linkButton =
            document.createElement("button");

        linkButton.type = "button";

        linkButton.className = "link-action";

        linkButton.setAttribute(
            "aria-label",
            `Send payment link to ${customer.name}`
        );

        linkButton.title =
            "Payment link integration is not connected yet";

        linkButton.disabled = true;

        linkButton.appendChild(createLinkIcon());


        // Call button
        const callButton =
            document.createElement("button");

        callButton.type = "button";

        callButton.className =
            "btn btn-primary call-action";

        const phoneIcon = document.createElement("i");

        phoneIcon.className = "fa-solid fa-phone";

        phoneIcon.setAttribute("aria-hidden", "true");


        const callLabel = document.createElement("span");

        callLabel.textContent = "Call";


        callButton.append(phoneIcon, callLabel);


        callButton.addEventListener("click", () => {

            if (!customer.id) {
                alert("Customer ID is missing.");
                return;
            }

            window.location.href =
                `/agent.html?cust_id=${encodeURIComponent(customer.id)}`;

        });


        actions.append(linkButton, callButton);

        actionCell.appendChild(actions);


        // =================================
        // ADD ALL CELLS TO ROW
        // =================================

        row.append(
            customerCell,
            productCell,
            outstandingCell,
            overdueCell,
            outcomeCell,
            actionCell
        );


        tableBody.appendChild(row);

    });


    customerCount.textContent =
        `Showing ${customers.length} of ${allCustomers.length} customers`;

}


// ========================================
// SEARCH AND FILTER CUSTOMERS
// ========================================


function filterCustomers() {

    const searchInput =
        document.getElementById("customerSearch");

    const searchTerm =
        searchInput.value.trim().toLowerCase();


    // Search and product filtering
    const filteredCustomers = allCustomers.filter(customer => {

        const name =
            String(customer.name || "").toLowerCase();

        const id =
            String(customer.id || "").toLowerCase();

        const product =
            String(customer.product || "");


        const matchesSearch =
            name.includes(searchTerm) ||
            id.includes(searchTerm);


        const matchesProduct =
            !selectedProduct ||
            product === selectedProduct;


        return matchesSearch && matchesProduct;

    });


    // Sort by highest overdue amount first
    filteredCustomers.sort((a, b) => {

        return (
            (Number(b.overdue_amt) || 0) -
            (Number(a.overdue_amt) || 0)
        );

    });


    renderCustomerTable(filteredCustomers);

}



function exportCustomersToCSV() {

    if (allCustomers.length === 0) {
        alert("No customers available to export.");
        return;
    }

    const headers = [
        "id",
        "name",
        "product",
        "outstanding",
        "overdue",
        "overdue_amt",
        "due_date"
    ];

    function escapeCSV(value) {

        let text = String(value ?? "");

        if (/^[\s]*[=+\-@]/.test(text)) {
            text = "'" + text;
        }

        return `"${text.replace(/"/g, '""')}"`;
    }

    const rows = allCustomers.map(customer =>
        headers.map(header =>
            escapeCSV(customer[header])
        ).join(",")
    );

    const csvContent = [
        headers.map(escapeCSV).join(","),
        ...rows
    ].join("\r\n");

    const blob = new Blob(
        ["\uFEFF" + csvContent],
        { type: "text/csv;charset=utf-8;" }
    );

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download = "payment-collection-customers.csv";

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
}

// ========================================
// INITIALIZE SEARCH AND FILTER
// ========================================


function initializeCustomerFilters() {

    const searchInput =
        document.getElementById("customerSearch");

    const exportButton =
        document.getElementById("exportCustomersBtn");


    // Search whenever the user types
    searchInput.addEventListener(
        "input",
        filterCustomers
    );


    // Export customer records
    exportButton.addEventListener(
        "click",
        exportCustomersToCSV
    );

}




// ========================================
// RENDER OVERDUE BY PRODUCT
// ========================================

function renderOverdueByProduct(customers) {

    const productList =
        document.getElementById("productOverdueList");

    const summary =
        document.getElementById("productOverdueSummary");

    const insight =
        document.getElementById("productOverdueInsight");


    // Group overdue amounts by loan product
    const productTotals = new Map();

    customers.forEach(customer => {

        const product =
            String(customer.product || "").trim();

        if (!product) return;

        const overdue =
            Math.max(0, Number(customer.overdue_amt) || 0);

        productTotals.set(
            product,
            (productTotals.get(product) || 0) + overdue
        );

    });


    // Convert Map into an array
    const products = Array.from(
        productTotals,
        ([name, amount]) => ({ name, amount })
    );


    // Sort highest overdue product first
    products.sort((a, b) => b.amount - a.amount);


    // Calculate total overdue
    const totalOverdue = products.reduce(
        (total, product) => total + product.amount,
        0
    );


    // Update heading summary
    summary.textContent =
        `${currencyFormatter.format(totalOverdue)} across ${products.length} products`;


    // Clear old chart rows
    productList.replaceChildren();


    // Handle empty data
    if (products.length === 0 || totalOverdue === 0) {

        const message = document.createElement("p");

        message.className = "summary-loading";
        message.textContent = "No overdue amounts to display.";

        productList.appendChild(message);

        insight.textContent = "";

        return;
    }


    // Find highest overdue amount
    const maximumAmount = Math.max(
        ...products.map(product => product.amount)
    );


    // Generate each product row
    products.forEach(product => {

        const row = document.createElement("div");

        row.className = "product-overdue-row";


        // PRODUCT NAME
        const name = document.createElement("span");

        name.className = "product-overdue-name";
        name.textContent = product.name;


        // PROGRESS BAR
        const bar = document.createElement("div");

        bar.className = "product-overdue-bar";


        const fill = document.createElement("div");

        fill.className = "product-overdue-fill";


        // Bar width relative to the largest product
        const barWidth =
            (product.amount / maximumAmount) * 100;

        fill.style.width = `${barWidth}%`;

        bar.appendChild(fill);


        // AMOUNT AND PERCENTAGE
        const value = document.createElement("div");

        value.className = "product-overdue-value";


        const amount = document.createElement("span");

        amount.className = "product-overdue-amount";

        amount.textContent =
            currencyFormatter.format(product.amount);


        const percentage = document.createElement("span");

        percentage.className = "product-overdue-percent";

        const share =
            Math.round((product.amount / totalOverdue) * 100);

        percentage.textContent = `${share}%`;


        value.append(amount, percentage);


        // Add complete row
        row.append(name, bar, value);

        productList.appendChild(row);

    });


    // Generate dynamic insight
    const highestProduct = products[0];

    const highestShare = Math.round(
        (highestProduct.amount / totalOverdue) * 100
    );

    insight.textContent =
        `${highestProduct.name} accounts for ${highestShare}% of total overdue. Prioritize these customers.`;

}


// ========================================
// LOAD DASHBOARD
// ========================================


async function loadDashboard() {

    const statusElement =
        document.getElementById("dashboardLoadStatus");

    try {

        statusElement.textContent =
            "Loading dashboard data...";


        // STEP 1: Fetch all customers
        allCustomers = await fetchCustomers();


        if (!Array.isArray(allCustomers)) {
            throw new Error("Invalid customer data received.");
        }


        // STEP 2: Calculate statistics
        const stats =
            calculateStatistics(allCustomers);


        // STEP 3: Update statistics cards
        displayStatistics(stats);

        // STEP 4: Render overdue by product
        renderOverdueByProduct(allCustomers);

        // Update overdue customer count in Quick Actions
        document.getElementById("quickOverdueCount").textContent =
            stats.overdueCustomers;


        // STEP 5: Update customer count in heading
        document.getElementById(
            "customerTotalBadge"
        ).textContent = allCustomers.length;


        // STEP 6: Generate product filter chips
        renderProductFilters(allCustomers);


        // STEP 7: Render customer table
        filterCustomers();


        statusElement.textContent = "";


    } catch (error) {

        console.error("Dashboard Error:", error);

        statusElement.textContent =
            "Unable to load dashboard data. Please try again.";

        document.querySelectorAll(".stat-value").forEach(element => {
            element.textContent = "—";
        });

        document.getElementById(
            "customerTotalBadge"
        ).textContent = "—";

        document.getElementById(
            "productFilters"
        ).replaceChildren();

        const tableBody =
            document.getElementById("customersTableBody");

        tableBody.textContent =
            "Unable to load customers.";
    }
}



// ========================================
// INITIALIZE DASHBOARD
// ========================================

initializeCustomerFilters();

loadDashboard();

// // Update total customer count in heading
// document.getElementById("customerTotalBadge").textContent =
//     allCustomers.length;

// // Generate product filter chips
// renderProductFilters(allCustomers);

// // Render customer table
// filterCustomers();
