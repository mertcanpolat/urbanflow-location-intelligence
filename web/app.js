let geoJsonLayer;
let hourlyDemandChart;
let dailyDemandChart;
let selectedZoneLayer;
let demandLegend;

let demandBreaks = [0, 0, 0];

const zoneLayersById = new Map();

const map = L.map("map").setView(
    [40.73, -73.93],
    10
);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);

createDemandLegend();

function getDemandColor(tripCount) {
    const count = Number(tripCount || 0);

    const [
        firstBreak,
        secondBreak,
        thirdBreak
    ] = demandBreaks;

    if (count <= 0) {
        return "#f3f4f6";
    }

    if (count > thirdBreak) {
        return "#991b1b";
    }

    if (count > secondBreak) {
        return "#ef4444";
    }

    if (count > firstBreak) {
        return "#fca5a5";
    }

    return "#fee2e2";
}

function zoneStyle(feature) {
    return {
        fillColor: getDemandColor(
            feature.properties.trip_count
        ),
        weight: 1,
        color: "#374151",
        fillOpacity: 0.7
    };
}

function highlightFeature(event) {
    const layer = event.target;

    layer.setStyle({
        weight: 3,
        color: "#111827",
        fillOpacity: 0.85
    });

    layer.bringToFront();
}

function resetHighlight(event) {
    const layer = event.target;

    if (!geoJsonLayer) {
        return;
    }

    if (layer === selectedZoneLayer) {
        layer.setStyle({
            weight: 4,
            color: "#111827",
            fillOpacity: 0.9
        });

        return;
    }

    geoJsonLayer.resetStyle(layer);
}

function formatNullableNumber(value, digits = 2) {
    if (value === null || value === undefined) {
        return "-";
    }

    return Number(value).toLocaleString(
        "tr-TR",
        {
            minimumFractionDigits: digits,
            maximumFractionDigits: digits
        }
    );
}

function onEachFeature(feature, layer) {
    const properties = feature.properties;
    zoneLayersById.set(
        Number(properties.location_id),
        layer
    );

    layer.bindPopup(`
        <strong>${properties.zone_name}</strong><br>
        Borough: ${properties.borough}<br>
        Location ID: ${properties.location_id}<br>
        Pickup sayısı:
        ${Number(
        properties.trip_count || 0
    ).toLocaleString("tr-TR")}<br>
        Ortalama mesafe:
        ${formatNullableNumber(
        properties.avg_trip_distance
    )}<br>
        Ortalama tutar:
        ${formatNullableNumber(
        properties.avg_total_amount
    )}
    `);

    layer.on({
        mouseover: highlightFeature,

        mouseout: resetHighlight,

        click: () => {
            if (selectedZoneLayer) {
                geoJsonLayer.resetStyle(
                    selectedZoneLayer
                );
            }

            selectedZoneLayer = layer;

            layer.setStyle({
                weight: 4,
                color: "#111827",
                fillOpacity: 0.9
            });

            layer.bringToFront();

            loadHourlyDemand(
                properties.location_id,
                `${properties.zone_name} · ${properties.borough}`
            );
        }
    });
}

function buildGeoJsonUrl() {
    const borough = document
        .getElementById("borough-filter")
        .value;

    const hour = document
        .getElementById("hour-filter")
        .value;

    const parameters = new URLSearchParams();

    if (borough) {
        parameters.set("borough", borough);
    }

    if (hour !== "") {
        parameters.set("hour", hour);
    }

    const queryString = parameters.toString();

    return queryString
        ? `/api/v1/zones/geojson?${queryString}`
        : "/api/v1/zones/geojson";
}

async function loadBoroughs() {
    const response = await fetch("/api/v1/boroughs");

    if (!response.ok) {
        throw new Error(
            `Borough API hatası: ${response.status}`
        );
    }

    const boroughs = await response.json();
    const select = document.getElementById(
        "borough-filter"
    );

    for (const borough of boroughs) {
        const option = document.createElement("option");

        option.value = borough;
        option.textContent = borough;

        select.appendChild(option);
    }
}

function populateHours() {
    const select = document.getElementById("hour-filter");

    for (let hour = 0; hour <= 23; hour += 1) {
        const option = document.createElement("option");

        option.value = hour;
        option.textContent =
            `${hour.toString().padStart(2, "0")}:00`;

        select.appendChild(option);
    }
}

async function loadMapData() {
    const geojson = await fetchJson(
        buildFilteredApiUrl(
            "/api/v1/zones/geojson"
        )
    );

    const features = Array.isArray(
        geojson.features
    )
        ? geojson.features
        : [];

    const featuresWithDemand =
        features.filter((feature) => {
            return Number(
                feature.properties?.trip_count || 0
            ) > 0;
        });

    if (featuresWithDemand.length === 0) {
        clearMapData();
        return false;
    }

    updateDemandBreaks(geojson);
    updateDemandLegend();

    if (geoJsonLayer) {
        map.removeLayer(geoJsonLayer);
    }

    zoneLayersById.clear();

    geoJsonLayer = L.geoJSON(
        geojson,
        {
            style: zoneStyle,
            onEachFeature
        }
    ).addTo(map);

    window.setTimeout(() => {
        map.invalidateSize();
    }, 100);
    
    return true;
}

document
    .getElementById("apply-filters")
    .addEventListener("click", () => {
    if (!validateDateFilters()) {
        return;
    }

    refreshDashboard();
});

document
    .getElementById("reset-filters")
    .addEventListener("click", () => {
        document.getElementById(
            "borough-filter"
        ).value = "";

        document.getElementById(
            "hour-filter"
        ).value = "";

        document.getElementById(
            "weekday-filter"
        ).value = "";

        document.getElementById(
            "date-from-filter"
        ).value = "";

        document.getElementById(
            "date-to-filter"
        ).value = "";

        refreshDashboard();
    });

async function initializeApplication() {
    try {
        populateHours();
        await loadBoroughs();
        await refreshDashboard();
    } catch (error) {
        console.error(
            "Uygulama başlangıç hatası:",
            error
        );

        document.getElementById("status").textContent =
            `Uygulama başlatılamadı: ${error.message}`;
    }
}

initializeApplication();

function normalizeHourlyData(hourlyData) {
    const demandByHour = new Map();

    for (const item of hourlyData) {
        demandByHour.set(
            Number(item.pickup_hour),
            Number(item.trip_count || 0)
        );
    }

    const labels = [];
    const values = [];

    for (let hour = 0; hour <= 23; hour += 1) {
        labels.push(
            `${hour.toString().padStart(2, "0")}:00`
        );

        values.push(
            demandByHour.get(hour) || 0
        );
    }

    return {
        labels,
        values
    };
}

function renderHourlyChart(hourlyData, zoneName) {
    const normalized = normalizeHourlyData(hourlyData);

    const canvas = document.getElementById(
        "hourly-demand-chart"
    );

    const context = canvas.getContext("2d");

    if (hourlyDemandChart) {
        hourlyDemandChart.destroy();
    }

    hourlyDemandChart = new Chart(
        context,
        {
            type: "bar",

            data: {
                labels: normalized.labels,

                datasets: [
                    {
                        label: "Pickup sayısı",
                        data: normalized.values,
                        borderWidth: 1
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    intersect: false,
                    mode: "index"
                },

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {
                            label(context) {
                                return (
                                    "Pickup: "
                                    + Number(
                                        context.raw
                                    ).toLocaleString("tr-TR")
                                );
                            }
                        }
                    }
                },

                scales: {
                    x: {
                        ticks: {
                            maxRotation: 90,
                            minRotation: 90,
                            autoSkip: true,
                            maxTicksLimit: 12
                        }
                    },

                    y: {
                        beginAtZero: true,

                        ticks: {
                            callback(value) {
                                return Number(
                                    value
                                ).toLocaleString("tr-TR");
                            }
                        }
                    }
                }
            }
        }
    );

    document.getElementById(
        "selected-zone-name"
    ).textContent = zoneName;
}

async function loadHourlyDemand(
    locationId,
    zoneName
) {
    try {
        const hourlyData = await fetchJson(
            buildHourlyDemandUrl(locationId)
        );

        const hasDemand =
            Array.isArray(hourlyData)
            && hourlyData.some(
                (item) =>
                    Number(
                        item.trip_count || 0
                    ) > 0
            );

        if (!hasDemand) {
            clearHourlyChart(
                `${zoneName}: seçilen dönemde veri yok`
            );

            return;
        }

        renderHourlyChart(
            hourlyData,
            `${zoneName} · `
            + getHourlyChartFilterLabel()
        );
    } catch (error) {
        console.error(
            "Saatlik grafik hatası:",
            error
        );

        clearHourlyChart(
            "Saatlik veriler yüklenemedi."
        );

        setDashboardStatus(
            error.message,
            "error"
        );
    }
}

function buildRankingUrl() {
    const borough = document
        .getElementById("borough-filter")
        .value;

    const hour = document
        .getElementById("hour-filter")
        .value;

    const parameters = new URLSearchParams();

    parameters.set("limit", "10");

    if (borough) {
        parameters.set("borough", borough);
    }

    if (hour !== "") {
        parameters.set("hour", hour);
    }

    return (
        "/api/v1/zones/ranking?"
        + parameters.toString()
    );
}

function selectZoneLayer(locationId) {
    const layer = zoneLayersById.get(
        Number(locationId)
    );

    if (!layer) {
        return;
    }

    if (selectedZoneLayer) {
        geoJsonLayer.resetStyle(
            selectedZoneLayer
        );
    }

    selectedZoneLayer = layer;

    layer.setStyle({
        weight: 4,
        color: "#111827",
        fillOpacity: 0.9
    });

    layer.bringToFront();
    map.fitBounds(layer.getBounds(), {
        maxZoom: 13
    });

    layer.openPopup();
}

function renderZoneRanking(zones) {
    const container = document.getElementById(
        "zone-ranking"
    );

    container.innerHTML = "";

    if (zones.length === 0) {
        container.innerHTML = `
            <p class="ranking-message">
                Filtrelere uygun bölge bulunamadı.
            </p>
        `;

        return;
    }

    zones.forEach((zone, index) => {
        const button = document.createElement(
            "button"
        );

        button.type = "button";
        button.className = "ranking-item";

        button.innerHTML = `
            <span class="ranking-position">
                ${index + 1}
            </span>

            <span class="ranking-zone">
                <strong>
                    ${zone.zone_name}
                </strong>

                <span>
                    ${zone.borough}
                </span>
            </span>

            <span class="ranking-value">
                ${Number(
            zone.trip_count || 0
        ).toLocaleString("tr-TR")}
            </span>
        `;

        button.addEventListener(
            "click",
            () => {
                selectZoneLayer(
                    zone.location_id
                );

                loadHourlyDemand(
                    zone.location_id,
                    `${zone.zone_name} · ${zone.borough}`
                );
            }
        );

        container.appendChild(button);
    });
}

async function loadZoneRanking() {
    const data = await fetchJson(
        buildFilteredApiUrl(
            "/api/v1/zones/ranking",
            {
                limit: 10
            }
        )
    );

    if (
        !Array.isArray(data)
        || data.length === 0
    ) {
        clearZoneRanking();
        return false;
    }

    renderZoneRanking(data);

    return true;
}

function resetHourlySelection() {
    selectedZoneLayer = null;

    document.getElementById(
        "selected-zone-name"
    ).textContent =
        "Haritadan bir bölge seçin";

    if (hourlyDemandChart) {
        hourlyDemandChart.destroy();
        hourlyDemandChart = null;
    }
}

async function refreshDashboard() {
    if (!validateDateFilters()) {
        return;
    }

    setDashboardLoading(true);

    setDashboardStatus(
        "Veriler yükleniyor...",
        "info"
    );

    clearHourlyChart(
        "Haritadan bir bölge seçin"
    );

    try {
        const [
            mapHasData,
            summaryHasData,
            trendHasData
        ] = await Promise.all([
            loadMapData(),
            loadDashboardSummary(),
            loadDailyTrend()
        ]);

        const rankingHasData =
            await loadZoneRanking();

        const dashboardHasData =
            mapHasData
            || summaryHasData
            || trendHasData
            || rankingHasData;

        if (!dashboardHasData) {
            clearDashboardData();

            setDashboardStatus(
                "Seçilen filtreler için veri bulunamadı.",
                "warning"
            );

            return;
        }

        setDashboardStatus(
            "Dashboard güncellendi.",
            "success"
        );
    } catch (error) {
        console.error(
            "Dashboard yükleme hatası:",
            error
        );

        clearDashboardData(
            "Veriler yüklenemedi."
        );

        setDashboardStatus(
            error.message
                || "Veriler yüklenirken hata oluştu.",
            "error"
        );
    } finally {
        setDashboardLoading(false);
    }
}

function buildSummaryUrl() {
    const borough = document
        .getElementById("borough-filter")
        .value;

    const hour = document
        .getElementById("hour-filter")
        .value;

    const parameters = new URLSearchParams();

    if (borough) {
        parameters.set("borough", borough);
    }

    if (hour !== "") {
        parameters.set("hour", hour);
    }

    const queryString = parameters.toString();

    return queryString
        ? `/api/v1/dashboard/summary?${queryString}`
        : "/api/v1/dashboard/summary";
}

async function loadDashboardSummary() {
    try {
        const response = await fetch(
            buildFilteredApiUrl(
                "/api/v1/dashboard/summary"
            )
        );

        if (!response.ok) {
            throw new Error(
                `Summary API hatası: ${response.status}`
            );
        }

        const summary = await response.json();

        const totalTrips = Number(
            summary.total_trips || 0
        );

        if (totalTrips <= 0) {
            clearDashboardSummary();
            return false;
        }

        setElementText(
            "zone-count",
            Number(
                summary.active_zones || 0
            ).toLocaleString("tr-TR")
        );

        setElementText(
            "trip-count",
            totalTrips.toLocaleString("tr-TR")
        );

        setElementText(
            "average-amount",
            summary.avg_total_amount !== null
                ? `$${Number(
                    summary.avg_total_amount
                ).toFixed(2)}`
                : "—"
        );

        setElementText(
            "average-distance",
            summary.avg_trip_distance !== null
                ? Number(
                    summary.avg_trip_distance
                ).toFixed(2)
                : "—"
        );

        return true;
    } catch (error) {
        console.error(
            "Summary yükleme hatası:",
            error
        );

        clearDashboardSummary();
        throw error;
    }
}

function buildDailyTrendUrl() {
    const borough = document
        .getElementById("borough-filter")
        .value;

    const hour = document
        .getElementById("hour-filter")
        .value;

    const parameters = new URLSearchParams();

    if (borough) {
        parameters.set("borough", borough);
    }

    if (hour !== "") {
        parameters.set("hour", hour);
    }

    const queryString = parameters.toString();

    return queryString
        ? `/api/v1/dashboard/daily-trend?${queryString}`
        : "/api/v1/dashboard/daily-trend";
}

function renderDailyDemandChart(dailyData) {
    const canvas = document.getElementById(
        "daily-demand-chart"
    );

    const context = canvas.getContext("2d");

    if (dailyDemandChart) {
        dailyDemandChart.destroy();
    }

    const labels = dailyData.map((item) => {
        const date = new Date(
            `${item.pickup_date}T00:00:00`
        );

        return date.toLocaleDateString(
            "tr-TR",
            {
                day: "2-digit",
                month: "2-digit"
            }
        );
    });

    const values = dailyData.map(
        (item) => Number(item.trip_count || 0)
    );

    dailyDemandChart = new Chart(
        context,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    {
                        label: "Yolculuk sayısı",
                        data: values,
                        borderWidth: 2,
                        pointRadius: 2,
                        tension: 0.25
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    intersect: false,
                    mode: "index"
                },

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {
                            label(context) {
                                return (
                                    "Yolculuk: "
                                    + Number(
                                        context.raw
                                    ).toLocaleString("tr-TR")
                                );
                            }
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,

                        ticks: {
                            callback(value) {
                                return Number(
                                    value
                                ).toLocaleString("tr-TR");
                            }
                        }
                    }
                }
            }
        }
    );
}

async function loadDailyTrend() {
    const data = await fetchJson(
        buildFilteredApiUrl(
            "/api/v1/dashboard/daily-trend"
        )
    );

    if (
        !Array.isArray(data)
        || data.length === 0
    ) {
        clearDailyTrendChart();
        return false;
    }

    const hasDemand = data.some(
        (item) =>
            Number(item.trip_count || 0) > 0
    );

    if (!hasDemand) {
        clearDailyTrendChart();
        return false;
    }

    renderDailyDemandChart(data);

    return true;
}

function getDashboardFilterParameters() {
    const borough = document
        .getElementById("borough-filter")
        .value;

    const hour = document
        .getElementById("hour-filter")
        .value;

    const weekday = document
        .getElementById("weekday-filter")
        .value;

    const dateFrom = document
        .getElementById("date-from-filter")
        .value;

    const dateTo = document
        .getElementById("date-to-filter")
        .value;

    const parameters = new URLSearchParams();

    if (borough) {
        parameters.set("borough", borough);
    }

    if (hour !== "") {
        parameters.set("hour", hour);
    }

    if (weekday !== "") {
        parameters.set("weekday", weekday);
    }

    if (dateFrom !== "") {
        parameters.set("date_from", dateFrom);
    }

    if (dateTo !== "") {
        parameters.set("date_to", dateTo);
    }
    return parameters;
}


function buildFilteredApiUrl(
    endpoint,
    additionalParameters = {}
) {
    const parameters =
        getDashboardFilterParameters();

    for (
        const [key, value]
        of Object.entries(additionalParameters)
    ) {
        if (
            value !== null
            && value !== undefined
            && value !== ""
        ) {
            parameters.set(
                key,
                String(value)
            );
        }
    }

    const queryString =
        parameters.toString();

    return queryString
        ? `${endpoint}?${queryString}`
        : endpoint;
}

function validateDateFilters() {
    const dateFrom = document
        .getElementById("date-from-filter")
        .value;

    const dateTo = document
        .getElementById("date-to-filter")
        .value;

    if (
        dateFrom
        && dateTo
        && dateFrom > dateTo
    ) {
        document.getElementById(
            "status"
        ).textContent =
            "Başlangıç tarihi bitiş tarihinden sonra olamaz";

        return false;
    }

    return true;
}

function buildHourlyDemandUrl(locationId) {
    const parameters =
        getDashboardFilterParameters();

    parameters.delete("borough");
    parameters.delete("hour");

    const queryString = parameters.toString();

    const endpoint =
        `/api/v1/zones/${locationId}/hourly`;

    return queryString
        ? `${endpoint}?${queryString}`
        : endpoint;
}

function getHourlyChartFilterLabel() {
    const weekdaySelect = document.getElementById(
        "weekday-filter"
    );

    const weekdayText =
        weekdaySelect.value === ""
            ? "Tüm günler"
            : weekdaySelect.options[
                weekdaySelect.selectedIndex
            ].textContent;

    const dateFrom = document
        .getElementById("date-from-filter")
        .value;

    const dateTo = document
        .getElementById("date-to-filter")
        .value;

    let dateText = "Tüm tarih aralığı";

    if (dateFrom && dateTo) {
        dateText = `${dateFrom} – ${dateTo}`;
    } else if (dateFrom) {
        dateText = `${dateFrom} sonrası`;
    } else if (dateTo) {
        dateText = `${dateTo} öncesi`;
    }

    return `${weekdayText} · ${dateText}`;
}

function calculateQuantile(sortedValues, quantile) {
    if (sortedValues.length === 0) {
        return 0;
    }

    const position =
        (sortedValues.length - 1) * quantile;

    const lowerIndex = Math.floor(position);
    const upperIndex = Math.ceil(position);

    const lowerValue = sortedValues[lowerIndex];
    const upperValue = sortedValues[upperIndex];

    if (lowerIndex === upperIndex) {
        return lowerValue;
    }

    const fraction = position - lowerIndex;

    return (
        lowerValue
        + (upperValue - lowerValue) * fraction
    );
}

function updateDemandBreaks(geojson) {
    const values = geojson.features
        .map((feature) =>
            Number(
                feature.properties.trip_count || 0
            )
        )
        .filter((value) => value > 0)
        .sort((a, b) => a - b);

    if (values.length === 0) {
        demandBreaks = [0, 0, 0];
        return;
    }

    demandBreaks = [
        calculateQuantile(values, 0.25),
        calculateQuantile(values, 0.50),
        calculateQuantile(values, 0.75)
    ];

    console.log(
        "Dinamik talep eşikleri:",
        demandBreaks
    );
}

function formatLegendNumber(value) {
    return Math.round(Number(value || 0))
        .toLocaleString("tr-TR");
}

function getDemandLegendRanges() {
    const [
        rawFirstBreak,
        rawSecondBreak,
        rawThirdBreak
    ] = demandBreaks;

    const firstBreak = Math.round(
        Number(rawFirstBreak || 0)
    );

    const secondBreak = Math.round(
        Number(rawSecondBreak || 0)
    );

    const thirdBreak = Math.round(
        Number(rawThirdBreak || 0)
    );

    if (
        firstBreak === 0
        && secondBreak === 0
        && thirdBreak === 0
    ) {
        return [];
    }

    const ranges = [
        {
            color: "#fee2e2",
            minimum: 1,
            maximum: firstBreak
        },
        {
            color: "#fca5a5",
            minimum: firstBreak + 1,
            maximum: secondBreak
        },
        {
            color: "#ef4444",
            minimum: secondBreak + 1,
            maximum: thirdBreak
        },
        {
            color: "#991b1b",
            minimum: thirdBreak + 1,
            maximum: null
        }
    ];

    return ranges
        .filter((range) => {
            if (range.maximum === null) {
                return true;
            }

            return range.minimum <= range.maximum;
        })
        .map((range) => {
            let label;

            if (range.maximum === null) {
                label =
                    `${formatLegendNumber(
                        range.minimum
                    )}+`;
            } else {
                label =
                    `${formatLegendNumber(
                        range.minimum
                    )} – `
                    + `${formatLegendNumber(
                        range.maximum
                    )}`;
            }

            return {
                color: range.color,
                label
            };
        })
        .concat([
            {
                color: "#f3f4f6",
                label: "Veri yok"
            }
        ]);
}

function createDemandLegend() {
    demandLegend = L.control({
        position: "bottomright"
    });

    demandLegend.onAdd = function () {
        const container = L.DomUtil.create(
            "div",
            "demand-legend"
        );

        container.innerHTML = `
            <div class="demand-legend-title">
                Yolculuk sayısı
            </div>

            <div
                id="demand-legend-content"
                class="demand-legend-content"
            ></div>
        `;

        L.DomEvent.disableClickPropagation(
            container
        );

        return container;
    };

    demandLegend.addTo(map);
}

function updateDemandLegend() {
    const legendContent =
        document.getElementById(
            "demand-legend-content"
        );

    if (!legendContent) {
        return;
    }

    const ranges = getDemandLegendRanges();

    if (ranges.length === 0) {
        legendContent.innerHTML = `
            <div class="demand-legend-empty">
                Gösterilecek veri yok
            </div>
        `;

        return;
    }

    legendContent.innerHTML = ranges
        .map((range) => `
            <div class="demand-legend-item">
                <span
                    class="demand-legend-color"
                    style="background:${range.color}"
                ></span>

                <span>
                    ${range.label}
                </span>
            </div>
        `)
        .join("");
}

function setDashboardStatus(message, type = "info") {
    const statusElement =
        document.getElementById("status");

    if (!statusElement) {
        return;
    }

    statusElement.textContent = message;

    statusElement.classList.remove(
        "status-info",
        "status-success",
        "status-warning",
        "status-error"
    );

    statusElement.classList.add(
        `status-${type}`
    );
}

async function fetchJson(url) {
    const response = await fetch(url);

    if (!response.ok) {
        let errorMessage =
            `API hatası: ${response.status}`;

        try {
            const errorData = await response.json();

            if (errorData.detail) {
                errorMessage = errorData.detail;
            }
        } catch {
            // API JSON hata cevabı döndürmediyse
            // varsayılan mesaj kullanılır.
        }

        throw new Error(errorMessage);
    }

    return response.json();
}

function setDashboardLoading(isLoading) {
    const applyButton =
        document.getElementById(
            "apply-filters"
        );

    const resetButton =
        document.getElementById(
            "reset-filters"
        );

    const loadingOverlay =
        document.getElementById(
            "dashboard-loading-overlay"
        );

    if (applyButton) {
        applyButton.disabled = isLoading;

        applyButton.textContent = isLoading
            ? "Yükleniyor..."
            : "Filtreleri Uygula";
    }

    if (resetButton) {
        resetButton.disabled = isLoading;
    }

    if (loadingOverlay) {
        loadingOverlay.classList.toggle(
            "is-visible",
            isLoading
        );

        loadingOverlay.setAttribute(
            "aria-hidden",
            String(!isLoading)
        );
    }

    document.body.setAttribute(
        "aria-busy",
        String(isLoading)
    );
}

function clearDashboardSummary() {
    setElementText("zone-count", "0");
    setElementText("trip-count", "0");
    setElementText("average-amount", "—");
    setElementText("average-distance", "—");
}

function clearMapData() {
    if (geoJsonLayer) {
        map.removeLayer(geoJsonLayer);
        geoJsonLayer = null;
    }

    zoneLayersById.clear();

    demandBreaks = [0, 0, 0];

    updateDemandLegend();
}

function clearHourlyChart(
    message = "Haritadan bir bölge seçin"
) {
    if (hourlyDemandChart) {
        hourlyDemandChart.destroy();
        hourlyDemandChart = null;
    }

    const selectedZoneName =
        document.getElementById(
            "selected-zone-name"
        );

    if (selectedZoneName) {
        selectedZoneName.textContent =
            message;
    }
}

function clearDailyTrendChart() {
    if (dailyDemandChart) {
        dailyDemandChart.destroy();
        dailyDemandChart = null;
    }

    const canvas =
        document.getElementById(
            "daily-demand-chart"
        );

    if (!canvas) {
        return;
    }

    const context = canvas.getContext("2d");

    context.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );
}

function clearZoneRanking(
    message = "Gösterilecek bölge bulunamadı."
) {
    const rankingContainer =
        document.getElementById(
            "zone-ranking"
        );

    if (!rankingContainer) {
        return;
    }

    rankingContainer.innerHTML = `
        <div class="empty-state">
            ${message}
        </div>
    `;
}

function clearDashboardData(
    message = "Seçilen filtreler için veri bulunamadı."
) {
    clearDashboardSummary();
    clearMapData();
    clearHourlyChart(message);
    clearDailyTrendChart();
    clearZoneRanking(message);
}

function setElementText(id, value) {
    const element = document.getElementById(id);

    if (!element) {
        console.warn(`HTML elementi bulunamadı: #${id}`);
        return;
    }

    element.textContent = value;
}

window.addEventListener("resize", () => {
    window.clearTimeout(
        window.urbanFlowResizeTimer
    );

    window.urbanFlowResizeTimer =
        window.setTimeout(() => {
            map.invalidateSize();
        }, 150);
});