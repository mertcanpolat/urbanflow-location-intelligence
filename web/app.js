let geoJsonLayer;
let hourlyDemandChart;
let dailyDemandChart;
let weekdayHourHeatmapChart;
let dailyDemandForecastChart;
let selectedZoneLayer;
let demandLegend;


const DEMAND_CLASSES = {
    0: {
        label: "Veri Yok",
        color: "#e5e7eb"
    },
    1: {
        label: "Çok Düşük",
        color: "#fee2e2"
    },
    2: {
        label: "Düşük",
        color: "#fca5a5"
    },
    3: {
        label: "Orta",
        color: "#fb7185"
    },
    4: {
        label: "Yüksek",
        color: "#ef4444"
    },
    5: {
        label: "Çok Yüksek",
        color: "#991b1b"
    }
};

const HOTSPOT_CLASSES = {
    "-2": {
        label: "Coldspot",
        color: "#1d4ed8"
    },
    "-1": {
        label: "Potansiyel Coldspot",
        color: "#93c5fd"
    },
    "0": {
        label: "Nötr",
        color: "#e5e7eb"
    },
    "1": {
        label: "Potansiyel Hotspot",
        color: "#fca5a5"
    },
    "2": {
        label: "Hotspot",
        color: "#b91c1c"
    }
};

const DEFAULT_MAP_CENTER = [40.73, -73.93];
const DEFAULT_MAP_ZOOM = 10;
const zoneLayersById = new Map();

const map = L.map("map").setView(
    DEFAULT_MAP_CENTER,
    DEFAULT_MAP_ZOOM
);

const WEEKDAY_LABELS = {
    1: "Pazartesi",
    2: "Salı",
    3: "Çarşamba",
    4: "Perşembe",
    5: "Cuma",
    6: "Cumartesi",
    7: "Pazar"
};

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);

createDemandLegend();

function getMapMode() {
    const select = document.getElementById(
        "map-mode-filter"
    );

    return select?.value || "demand";
}

function getDemandColor(demandClassId) {
    const classId = Number(
        demandClassId || 0
    );

    return (
        DEMAND_CLASSES[classId]?.color
        || DEMAND_CLASSES[0].color
    );
}

function getHotspotColor(hotspotScore) {
    const score = String(
        Number(hotspotScore || 0)
    );

    return (
        HOTSPOT_CLASSES[score]?.color
        || HOTSPOT_CLASSES["0"].color
    );
}

function zoneStyle(feature) {
    const properties =
        feature.properties || {};

    const fillColor =
        getMapMode() === "hotspot"
            ? getHotspotColor(
                properties.hotspot_score
            )
            : getDemandColor(
                properties.demand_class_id
            );

    return {
        fillColor,
        weight: 1,
        color: "#374151",
        fillOpacity: 0.72
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

function buildDemandPopup(properties) {
    return `
        <strong>${properties.zone_name}</strong><br>

        Borough:
        ${properties.borough}<br>

        Location ID:
        ${properties.location_id}<br>

        Talep sınıfı:
        <strong>
            ${properties.demand_class || "Veri Yok"}
        </strong><br>

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
    `;
}

function buildHotspotPopup(properties) {
    return `
        <strong>${properties.zone_name}</strong><br>

        Borough:
        ${properties.borough}<br>

        Location ID:
        ${properties.location_id}<br>

        Hotspot sınıfı:
        <strong>
            ${properties.hotspot_class || "Nötr"}
        </strong><br>

        Pickup sayısı:
        ${Number(
        properties.trip_count || 0
    ).toLocaleString("tr-TR")}<br>

        Komşu zone sayısı:
        ${Number(
        properties.neighbour_count || 0
    ).toLocaleString("tr-TR")}<br>

        Komşu ortalama talebi:
        ${Number(
        properties.neighbour_avg_trip_count || 0
    ).toLocaleString("tr-TR", {
        maximumFractionDigits: 2
    })}
    `;
}

function onEachFeature(feature, layer) {
    const properties = feature.properties;
    zoneLayersById.set(
        Number(properties.location_id),
        layer
    );

    const popupContent =
        getMapMode() === "hotspot"
            ? buildHotspotPopup(properties)
            : buildDemandPopup(properties);

    layer.bindPopup(popupContent);

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
            const clearSelectionButton =
                document.getElementById(
                    "clear-zone-selection"
                );

            if (clearSelectionButton) {
                clearSelectionButton.hidden = false;
            }

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

function buildMapDataUrl() {
    const endpoint =
        getMapMode() === "hotspot"
            ? "/api/v1/zones/hotspots"
            : "/api/v1/zones/geojson";

    return buildFilteredApiUrl(endpoint);
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

function updateMapView() {
    if (
        !geoJsonLayer
        || geoJsonLayer.getLayers().length === 0
    ) {
        map.setView(
            DEFAULT_MAP_CENTER,
            DEFAULT_MAP_ZOOM
        );

        return;
    }

    const borough = document
        .getElementById("borough-filter")
        .value;

    if (!borough) {
        map.setView(
            DEFAULT_MAP_CENTER,
            DEFAULT_MAP_ZOOM
        );

        return;
    }

    const bounds = geoJsonLayer.getBounds();

    if (bounds.isValid()) {
        map.fitBounds(
            bounds,
            {
                padding: [24, 24],
                maxZoom: 12,
                animate: true
            }
        );
    }
}

async function loadMapData() {
    const geojson = await fetchJson(
        buildMapDataUrl()
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
        updateMapView();
    }, 100);

    return true;
}

const mapModeFilter =
    document.getElementById(
        "map-mode-filter"
    );

if (mapModeFilter) {
    mapModeFilter.addEventListener(
        "change",
        () => {
            refreshDashboard();
        }
    );
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

        document.getElementById(
            "map-mode-filter"
        ).value = "demand";

        refreshDashboard();
    });

const clearZoneSelectionButton =
    document.getElementById(
        "clear-zone-selection"
    );

if (clearZoneSelectionButton) {
    clearZoneSelectionButton.addEventListener(
        "click",
        () => {
            resetHourlySelection();
        }
    );
}

async function initializeApplication() {
    try {
        populateHours();
        updateActiveFilterSummary();
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

    const emptyState = document.getElementById(
        "hourly-chart-empty"
    );

    if (emptyState) {
        emptyState.hidden = true;
    }

    canvas.hidden = false;
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

    const clearSelectionButton =
        document.getElementById(
            "clear-zone-selection"
        );

    if (clearSelectionButton) {
        clearSelectionButton.hidden = false;
    }

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
    if (
        selectedZoneLayer
        && geoJsonLayer
    ) {
        geoJsonLayer.resetStyle(
            selectedZoneLayer
        );
    }

    selectedZoneLayer = null;

    const clearSelectionButton =
        document.getElementById(
            "clear-zone-selection"
        );

    if (clearSelectionButton) {
        clearSelectionButton.hidden = true;
    }

    clearHourlyChart(
        "Haritadan bir bölge seçin"
    );
}

async function refreshDashboard() {
    if (!validateDateFilters()) {
        return;
    }


    updateActiveFilterSummary();
    resetHourlySelection();;
    setDashboardLoading(true);

    setDashboardStatus(
        "Veriler yükleniyor...",
        "info"
    );

    clearHourlyChart(
        "Haritadan bir bölge seçin"
    );

    clearDailyTrendChart(
        "Günlük talep verileri yükleniyor..."
    );

    clearWeekdayHourHeatmap(
        "Isı haritası yükleniyor..."
    );

    clearDailyDemandForecastChart(
        "Talep tahmini yükleniyor..."
    );

    try {
        const [
            mapHasData,
            summaryHasData,
            trendHasData,
            heatmapHasData,
            forecastHasData
        ] = await Promise.all([
            loadMapData(),
            loadDashboardSummary(),
            loadDailyTrend(),
            loadWeekdayHourHeatmap(),
            loadDailyDemandForecast()
        ]);

        const rankingHasData =
            await loadZoneRanking();

        const dashboardHasData =
            mapHasData
            || summaryHasData
            || trendHasData
            || heatmapHasData
            || forecastHasData
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

    const emptyState = document.getElementById(
        "daily-chart-empty"
    );

    if (emptyState) {
        emptyState.hidden = true;
    }

    canvas.hidden = false;
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

function formatFilterDate(dateValue) {
    if (!dateValue) {
        return null;
    }

    const date = new Date(
        `${dateValue}T00:00:00`
    );

    return date.toLocaleDateString(
        "tr-TR",
        {
            day: "2-digit",
            month: "2-digit",
            year: "numeric"
        }
    );
}

function updateActiveFilterSummary() {
    const mapModeSelect =
        document.getElementById(
            "map-mode-filter"
        );

    const boroughSelect =
        document.getElementById(
            "borough-filter"
        );

    const hourSelect =
        document.getElementById(
            "hour-filter"
        );

    const weekdaySelect =
        document.getElementById(
            "weekday-filter"
        );

    const dateFrom =
        document.getElementById(
            "date-from-filter"
        ).value;

    const dateTo =
        document.getElementById(
            "date-to-filter"
        ).value;

    const activeFilters = [];

    if (mapModeSelect.value === "hotspot") {
        activeFilters.push(
            "Hotspot Analizi"
        );
    }

    if (boroughSelect.value) {
        activeFilters.push(
            boroughSelect.options[
                boroughSelect.selectedIndex
            ].textContent
        );
    }

    if (hourSelect.value !== "") {
        activeFilters.push(
            hourSelect.options[
                hourSelect.selectedIndex
            ].textContent
        );
    }

    if (weekdaySelect.value !== "") {
        activeFilters.push(
            weekdaySelect.options[
                weekdaySelect.selectedIndex
            ].textContent
        );
    }

    const formattedFrom =
        formatFilterDate(dateFrom);

    const formattedTo =
        formatFilterDate(dateTo);

    if (formattedFrom && formattedTo) {
        activeFilters.push(
            `${formattedFrom} – ${formattedTo}`
        );
    } else if (formattedFrom) {
        activeFilters.push(
            `${formattedFrom} sonrası`
        );
    } else if (formattedTo) {
        activeFilters.push(
            `${formattedTo} öncesi`
        );
    }

    setElementText(
        "active-filter-text",
        activeFilters.length > 0
            ? activeFilters.join(" · ")
            : "Tüm veriler"
    );
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
            <div
                id="map-legend-title"
                class="demand-legend-title"
            >
                Talep sınıfı
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
    const legendTitle =
        document.getElementById(
            "map-legend-title"
        );

    const legendContent =
        document.getElementById(
            "demand-legend-content"
        );

    if (!legendContent) {
        return;
    }

    const isHotspot =
        getMapMode() === "hotspot";

    if (legendTitle) {
        legendTitle.textContent = isHotspot
            ? "Hotspot analizi"
            : "Talep sınıfı";
    }

    const classes = isHotspot
        ? [
            HOTSPOT_CLASSES["2"],
            HOTSPOT_CLASSES["1"],
            HOTSPOT_CLASSES["0"],
            HOTSPOT_CLASSES["-1"],
            HOTSPOT_CLASSES["-2"]
        ]
        : [
            DEMAND_CLASSES[5],
            DEMAND_CLASSES[4],
            DEMAND_CLASSES[3],
            DEMAND_CLASSES[2],
            DEMAND_CLASSES[1],
            DEMAND_CLASSES[0]
        ];

    legendContent.innerHTML = classes
        .map((item) => `
            <div class="demand-legend-item">
                <span
                    class="demand-legend-color"
                    style="background:${item.color}"
                ></span>

                <span>
                    ${item.label}
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

    updateDemandLegend();
}

function clearHourlyChart(
    message = "Haritadan bir bölge seçin"
) {
    if (hourlyDemandChart) {
        hourlyDemandChart.destroy();
        hourlyDemandChart = null;
    }

    const canvas = document.getElementById(
        "hourly-demand-chart"
    );

    const emptyState = document.getElementById(
        "hourly-chart-empty"
    );

    if (canvas) {
        canvas.hidden = true;
    }

    if (emptyState) {
        emptyState.textContent = message;
        emptyState.hidden = false;
    }

    const selectedZoneName =
        document.getElementById(
            "selected-zone-name"
        );

    if (selectedZoneName) {
        selectedZoneName.textContent = message;
    }
}

function clearDailyTrendChart(
    message = "Seçilen filtreler için günlük talep verisi bulunamadı."
) {
    if (dailyDemandChart) {
        dailyDemandChart.destroy();
        dailyDemandChart = null;
    }

    const canvas = document.getElementById(
        "daily-demand-chart"
    );

    const emptyState = document.getElementById(
        "daily-chart-empty"
    );

    if (canvas) {
        canvas.hidden = true;
    }

    if (emptyState) {
        emptyState.textContent = message;
        emptyState.hidden = false;
    }
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
    clearMapData();
    clearSummaryCards();
    clearDailyTrendChart(message);
    clearWeekdayHourHeatmap(message);
    clearDailyDemandForecastChart(message);
    clearZoneRanking(message);
    resetHourlySelection();
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

function buildWeekdayHourHeatmapUrl() {
    const parameters =
        getDashboardFilterParameters();

    parameters.delete("hour");
    parameters.delete("weekday");

    const queryString = parameters.toString();

    const endpoint =
        "/api/v1/dashboard/weekday-hour-heatmap";

    return queryString
        ? `${endpoint}?${queryString}`
        : endpoint;
}

function normalizeWeekdayHourHeatmap(data) {
    const demandByCell = new Map();

    for (const item of data) {
        const key =
            `${Number(item.weekday)}-${Number(item.pickup_hour)}`;

        demandByCell.set(
            key,
            Number(item.trip_count || 0)
        );
    }

    const cells = [];

    for (let weekday = 1; weekday <= 7; weekday += 1) {
        for (let hour = 0; hour <= 23; hour += 1) {
            const key = `${weekday}-${hour}`;

            cells.push({
                x: hour,
                y: weekday,
                v: demandByCell.get(key) || 0
            });
        }
    }

    return cells;
}

function getHeatmapColor(value, maximumValue) {
    if (maximumValue <= 0 || value <= 0) {
        return "rgba(241, 245, 249, 1)";
    }

    const intensity = value / maximumValue;

    if (intensity >= 0.75) {
        return "rgba(153, 27, 27, 0.95)";
    }

    if (intensity >= 0.50) {
        return "rgba(239, 68, 68, 0.88)";
    }

    if (intensity >= 0.25) {
        return "rgba(252, 165, 165, 0.88)";
    }

    return "rgba(254, 226, 226, 0.92)";
}

function renderWeekdayHourHeatmap(data) {
    const canvas = document.getElementById(
        "weekday-hour-heatmap-chart"
    );

    const emptyState = document.getElementById(
        "weekday-hour-heatmap-empty"
    );

    if (!canvas) {
        return;
    }

    const normalized =
        normalizeWeekdayHourHeatmap(data);

    const maximumValue = Math.max(
        ...normalized.map((item) => item.v),
        0
    );

    if (maximumValue <= 0) {
        clearWeekdayHourHeatmap();
        return;
    }

    if (emptyState) {
        emptyState.hidden = true;
    }

    canvas.hidden = false;

    if (weekdayHourHeatmapChart) {
        weekdayHourHeatmapChart.destroy();
    }

    const context = canvas.getContext("2d");

    weekdayHourHeatmapChart = new Chart(
        context,
        {
            type: "matrix",

            data: {
                datasets: [
                    {
                        label: "Yolculuk sayısı",
                        data: normalized,

                        backgroundColor(context) {
                            const value =
                                context.raw?.v || 0;

                            return getHeatmapColor(
                                value,
                                maximumValue
                            );
                        },

                        borderColor: "#ffffff",
                        borderWidth: 1,

                        width(context) {
                            const chartArea =
                                context.chart.chartArea;

                            if (!chartArea) {
                                return 10;
                            }

                            return (
                                chartArea.width / 24
                            ) - 1;
                        },

                        height(context) {
                            const chartArea =
                                context.chart.chartArea;

                            if (!chartArea) {
                                return 10;
                            }

                            return (
                                chartArea.height / 7
                            ) - 1;
                        }
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {
                            title(items) {
                                const item =
                                    items[0].raw;

                                return (
                                    WEEKDAY_LABELS[item.y]
                                    + " · "
                                    + `${String(item.x).padStart(2, "0")}:00`
                                );
                            },

                            label(context) {
                                return (
                                    "Yolculuk: "
                                    + Number(
                                        context.raw.v
                                    ).toLocaleString("tr-TR")
                                );
                            }
                        }
                    }
                },

                scales: {
                    x: {
                        type: "linear",
                        min: -0.5,
                        max: 23.5,
                        offset: false,

                        ticks: {
                            stepSize: 1,

                            callback(value) {
                                return Number.isInteger(value)
                                    ? String(value).padStart(2, "0")
                                    : "";
                            }
                        },

                        grid: {
                            display: false
                        },

                        title: {
                            display: true,
                            text: "Saat"
                        }
                    },

                    y: {
                        type: "linear",
                        min: 0.5,
                        max: 7.5,
                        reverse: true,

                        ticks: {
                            stepSize: 1,

                            callback(value) {
                                return (
                                    WEEKDAY_LABELS[value]
                                    || ""
                                );
                            }
                        },

                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );
}

async function loadWeekdayHourHeatmap() {
    const data = await fetchJson(
        buildWeekdayHourHeatmapUrl()
    );

    if (
        !Array.isArray(data)
        || data.length === 0
    ) {
        clearWeekdayHourHeatmap();
        return false;
    }

    const hasDemand = data.some(
        (item) =>
            Number(item.trip_count || 0) > 0
    );

    if (!hasDemand) {
        clearWeekdayHourHeatmap();
        return false;
    }

    renderWeekdayHourHeatmap(data);

    return true;
}

function clearWeekdayHourHeatmap(
    message = "Seçilen filtreler için gün–saat talep verisi bulunamadı."
) {
    if (weekdayHourHeatmapChart) {
        weekdayHourHeatmapChart.destroy();
        weekdayHourHeatmapChart = null;
    }

    const canvas = document.getElementById(
        "weekday-hour-heatmap-chart"
    );

    const emptyState = document.getElementById(
        "weekday-hour-heatmap-empty"
    );

    if (canvas) {
        canvas.hidden = true;
    }

    if (emptyState) {
        emptyState.textContent = message;
        emptyState.hidden = false;
    }
}

function buildDailyDemandForecastUrl() {
    const parameters =
        getDashboardFilterParameters();

    parameters.delete("hour");
    parameters.delete("weekday");
    parameters.delete("date_from");
    parameters.delete("date_to");

    parameters.set(
        "forecast_days",
        "7"
    );

    parameters.set(
        "history_weeks",
        "4"
    );

    const queryString =
        parameters.toString();

    return (
        "/api/v1/forecast/daily-demand?"
        + queryString
    );
}

function renderDailyDemandForecastChart(data) {
    const canvas = document.getElementById(
        "daily-demand-forecast-chart"
    );

    const emptyState = document.getElementById(
        "forecast-chart-empty"
    );

    if (!canvas) {
        return;
    }

    if (emptyState) {
        emptyState.hidden = true;
    }

    canvas.hidden = false;

    if (dailyDemandForecastChart) {
        dailyDemandForecastChart.destroy();
    }

    const labels = data.map((item) => {
        const date = new Date(
            `${item.forecast_date}T00:00:00`
        );

        return date.toLocaleDateString(
            "tr-TR",
            {
                weekday: "short",
                day: "2-digit",
                month: "2-digit"
            }
        );
    });

    const predictedValues = data.map(
        (item) =>
            Number(
                item.predicted_trip_count || 0
            )
    );

    const lowerValues = data.map(
        (item) =>
            Number(
                item.lower_bound || 0
            )
    );

    const upperValues = data.map(
        (item) =>
            Number(
                item.upper_bound || 0
            )
    );

    const context = canvas.getContext("2d");

    dailyDemandForecastChart = new Chart(
        context,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    {
                        label: "Alt sınır",
                        data: lowerValues,
                        borderWidth: 0,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: "Üst sınır",
                        data: upperValues,
                        borderWidth: 0,
                        pointRadius: 0,
                        fill: "-1"
                    },
                    {
                        label: "Tahmini yolculuk",
                        data: predictedValues,
                        borderWidth: 3,
                        pointRadius: 4,
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
                        display: false,
                        position: "bottom",

                        labels: {
                            boxWidth: 12,
                            font: {
                                size: 10
                            }
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label(context) {
                                return (
                                    `${context.dataset.label}: `
                                    + Number(
                                        context.raw
                                    ).toLocaleString("tr-TR")
                                );
                            },

                            afterBody(items) {
                                const index =
                                    items[0].dataIndex;

                                return (
                                    "Örnek gün sayısı: "
                                    + Number(
                                        data[index]
                                            .sample_count || 0
                                    )
                                );
                            }
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: false,

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

async function loadDailyDemandForecast() {
    const data = await fetchJson(
        buildDailyDemandForecastUrl()
    );

    if (
        !Array.isArray(data)
        || data.length === 0
    ) {
        clearDailyDemandForecastChart();
        return false;
    }

    const hasForecast = data.some(
        (item) =>
            Number(
                item.predicted_trip_count || 0
            ) > 0
    );

    if (!hasForecast) {
        clearDailyDemandForecastChart();
        return false;
    }

    renderDailyDemandForecastChart(data);

    return true;
}

function clearDailyDemandForecastChart(
    message = "Talep tahmini bulunamadı."
) {
    if (dailyDemandForecastChart) {
        dailyDemandForecastChart.destroy();
        dailyDemandForecastChart = null;
    }

    const canvas = document.getElementById(
        "daily-demand-forecast-chart"
    );

    const emptyState = document.getElementById(
        "forecast-chart-empty"
    );

    if (canvas) {
        canvas.hidden = true;
    }

    if (emptyState) {
        emptyState.textContent = message;
        emptyState.hidden = false;
    }
}