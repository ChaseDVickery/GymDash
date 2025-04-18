import { resourceUsageUtils, resourceUsageDisplayUtils } from "./utils/usage.js";
import { dataUtils } from "./utils/data.js";
import { mediaUtils } from "./utils/media_utils.js";
import { apiURL } from "./utils/api_link.js";
// import * as d3 from "./libraries/d3.js";
// import { range } from "./libraries/d3.js";

console.log(d3);
console.log(JSZip);
// console.log(range);

const tryBtn        = document.querySelector("#try-api-btn");
const tryBtnOut     = document.querySelector("#try-api-out");
const testBtn       = document.querySelector("#test-api-btn");
const testBtnOut    = document.querySelector("#test-api-out");
const resourceBtn       = document.querySelector("#resource-usage-btn");
const resourceBtnOut    = document.querySelector("#resource-usage-out");
const scalarDataTestBtn       = document.querySelector("#scalar-test-btn");
const scalarDataTestBtnOut    = document.querySelector("#scalar-test-out");
const imageTestOut    = document.querySelector("#test-image");
const imageTestBtn    = document.querySelector("#image-test-btn");
const startSimTestBtn    = document.querySelector("#start-test-sim-btn");
const simTestTimestepsSlider = document.querySelector("#test-sim-steps-slider")
const queryProgressTestBtn = document.querySelector("#query-test-btn");
const stopSimTestBtn = document.querySelector("#stop-test-btn");
const fillHistoryTestBtn = document.querySelector("#fill-sim-history-test-btn");

// Constants
const defaultSimProgressUpdateInterval = 2000;  // (ms)
const defaultTimeout = 5.0; // (s)
const noID = "00000000-0000-0000-0000-000000000000"; // (str(UUID))

// Structures
// sim_selections store information
let sim_selections = {};

// Elements
const simSidebar = document.querySelector(".sim-selection-sidebar");
// Control
const startPanel                = document.querySelector("#start-panel");
const controlPanel              = document.querySelector("#control-panel");
const controlResponsePanel      = document.querySelector("#control-response-panel");
const queryPanel                = document.querySelector("#query-panel");
const queryResponsePanel        = document.querySelector("#query-response-panel");
const configNameEntry           = startPanel.querySelector("#config-name1");
const configKeyEntry            = startPanel.querySelector("#config-key1");
const configFamilyEntry         = startPanel.querySelector("#config-family1");
const configTypeEntry           = startPanel.querySelector("#config-type1");
const startSimBtn               = startPanel.querySelector("#start-sim-btn");


// Prefabs
const prefabSimSelectBox    = document.querySelector(".prefab.sim-selection-box");
const prefabKwarg        = document.querySelector(".prefab.kwarg");
prefabSimSelectBox.parentElement.removeChild(prefabSimSelectBox);
prefabKwarg.parentElement.removeChild(prefabKwarg);

const testImageOutputs = []

let testSimTimesteps = Number(simTestTimestepsSlider.value)

function call_random() {
    return fetch(apiURL("random"));
    // return fetch(apiURL("big-data1000");
    // return fetch(apiURL("big-data100000");
    // return fetch(apiURL("big-data1000000");
}


function displayNumberOutput(num) {
    tryBtnOut.textContent = num;
}
function displayTestNumberOutput(outputs) {
    testBtnOut.textContent = outputs;
}

function getNumber() {
    return call_random()
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            // .json() returns a Promise with the result being the JSON info
            return response.json();
        })
        .then((response) => {
            displayNumberOutput(response.value);
            return response;
        })
}

function timeGetNumber() {
    let start = Date.now();
    return call_random()
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            let time = Date.now() - start;
            return Promise.resolve({time});
        });
}

function testNumberAPI() {
    const numRequests = 1000;
    // Make n simultaneous API calls and time
    const times = [];
    const promises = [];
    for (let i = 0; i < numRequests; i++) {
        promises.push(
            timeGetNumber().then((response) => {
                times.push(response.time);
                return response;
            }).then((response) => {
                // console.log(times);
                displayTestNumberOutput(times);
            })
        );
    }
    Promise.all(promises).then((responses) => {
        // Process all the response times.
        const max = Math.max(...times);
        const min = Math.min(...times);
        const avg = times.reduce((sum, value) => {return sum + value;}) / times.length;
        const metricString = `You requested ${numRequests} numbers. We measured ${times.length} times. Metrics (min, avg, max): (${min/1000}, ${avg/1000}, ${max/1000})s`;
        console.log(metricString);
        setTimeout(displayTestNumberOutput(metricString), 0);
    });
}

function displayResourceUsage() {
    resourceUsageUtils.getResourceUsageDetailed()
    // resourceUsageUtils.getResourceUsageSimple()
        .then((usageValues) => {
            let usageString = "";
            for (const [key, value] of Object.entries(usageValues)) {
                usageString += `\t${key} = ${value}`;
            }
            usageString += `\tcpu=${(usageValues.cpus_percent.reduce((sum, value) => { return sum + value})/usageValues.cpus_percent.length).toFixed(2)}%`;
            usageString += `\tmemory=${((usageValues.memory_total - usageValues.memory_available)*100 / usageValues.memory_total).toFixed(2)}%`;
            usageString += `\tdisk=${((usageValues.disk_total - usageValues.disk_available)*100 / usageValues.disk_total).toFixed(2)}%`;
            resourceBtnOut.textContent = usageString;
        });
}

function displayScalarDataTest() {
    dataUtils.getAllNewScalars()
        .then((results) => {
            scalarDataTestBtnOut.textContent = `Recent logged results: ${results}`;
            console.log(results);
        });
}

function setImageOutput(index, imgSrc) {
    while (index >= testImageOutputs.length) {
        const img = document.createElement("img");
        document.body.appendChild(img);
        testImageOutputs.push(img);
    }
    testImageOutputs[index].src = imgSrc;
}
function displayVideoTest() {
    dataUtils.getAllNewImages()
        .then((results) => {
            for (let i = 0; i < results.length; i++) {
                setImageOutput(i, results[i]);
            }
            // console.log(results);
            // const gif_src = mediaUtils.binaryToGIF(results);
            // imageTestOut.src = gif_src;
        })
        .catch((error) => {

        });
}

function startSimTest() {
    const data = {
        name: "cartpole",
        sim_key: "my_custom_sim",
        // sim_key: "stable_baselines/ppo",
        sim_family: "",
        sim_type: "",
        kwargs: {
            "num_steps": testSimTimesteps,
            "episode_trigger": 50,
            "policy": "MlpPolicy",
            "env": "LunarLander-v3",
            "algorithm": "ppo"
        }
    };
    fetch(apiURL("start-new-test"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    })
    .then((response) => {
        const info = response.json();
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
}

function stopSimTest() {
    const simulationQuery = {
        id: "dummy_id",
        timeout: 0.0,
        stop_simulation: {
            triggered: true,
            value: "stop, please"
        }
    };
    fetch(apiURL("query-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(simulationQuery),
    })
    .then((response) => {
        const info = response.json();
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    })
}

function testQueryProgress() {
    const simulationQuery = {
        id: "dummy_id",
        timeout: 1.0,
        stop_simulation: {}, // This would contain fields 'triggered' and 'value'
        progress: {
            triggered: true,
            value: "give me this information, please",
        } // This would contain fields 'triggered' and 'value'
    };
    fetch(apiURL("query-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(simulationQuery),
    })
    .then((response) => {
        const info = response.json();
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    })
}

function queryProgress(simID, onlyStatus=False) {
    if (!validID(simID)) { return Promise.resolve({id: noID}); }
    const q = {
        id: simID,
        timeout: defaultTimeout,
        is_done:    { triggered: true, value: null, },
        cancelled:  { triggered: true, value: null, },
        failed:     { triggered: true, value: null, },
    };
    if (!onlyStatus) {
        q.progress = { triggered: true, value: null, };
    }
    return query(q);
}
function controlStopSim(simID) {
    if (!validID(simID)) { return Promise.resolve({id: noID}); }
    const q = {
        id: simID,
        timeout: defaultTimeout,
        stop_simulation: {triggered: true, value: null},
    };
    return query(q);
}
// Returns a promise of the simulation query
function query(queryBody) {
    queryBody.error_details = { triggered: true, value: null };
    console.log(`Sending query: ${queryBody}`);
    console.log(queryBody);
    return fetch(apiURL("query-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(queryBody),
    }).then((response) => { return response.json(); });
}


// Utils
function convertKwargValue(valueString) {
    // Return the input if it is not a string
    if (typeof valueString !== "string") { return valueString; }
    // Trim string
    valueString = valueString.trim();
    // Bool check
    if (valueString.toLowerCase() === "true")   { return true; }
    else if (valueString.toLowerCase() === "false")  { return false; }
    // If starts with a quote, then there's really no other
    // type it could be but string
    else if (valueString.startsWith('\"') || valueString.startsWith('\'')) {
        let startIdx = 0;
        let endIdx = valueString.length-1;
        // Find start index beyond quote marks
        while (startIdx < valueString.length) {
            if (valueString.charAt(startIdx) !== "\'" && valueString.charAt(startIdx) !== "\"") {
                break;
            }
            startIdx += 1;
        }
        // Find index right before final sequence of quotes
        while (endIdx >= 0) {
            if (valueString.charAt(endIdx) !== "\'" && valueString.charAt(endIdx) !== "\"") {
                endIdx += 1;
                break;
            }
            endIdx -= 1;
        }
        return valueString.substring(startIdx, endIdx);
    }
    // Try to convert to number
    else if (!Number.isNaN(Number(valueString))) {
        return Number(valueString);
    }
    // Just return the trimmed value
    else {
        return valueString;
    }
}
function getKwargs(elementWithKwargPanel) {
    const kwargArea = elementWithKwargPanel.querySelector(".kwarg-area");
    const allKwargEntries = kwargArea.querySelectorAll(".kwarg");
    const kwargs = {};
    for (const kwargEntry of allKwargEntries) {
        let key = kwargEntry.querySelector(".key").value.trim();
        let val = kwargEntry.querySelector(".value").value.trim();
        if (key === "") { continue; }
        if (val === "") { val = true; }
        const splitKey = key.split(/\s+/);
        key = splitKey.join("_");
        val = convertKwargValue(val);
        kwargs[key] = val;
    }
    return kwargs;
}

function updateAllSimSelectionProgress() {
    // Iterates all incomplete sim selections and queries their progress
    console.log("updateAllSimSelectionProgress: "+ sim_selections);
    for (const [simID, simSelection] of Object.entries(sim_selections)) {
        updateSimSelectionProgress(simID, simSelection);
    }
}
function updateSimSelectionProgress(simID, simSelection) {
    const meter = simSelection.querySelector(".radial-meter")
    // if (meter.classList.contains("complete")) { return; }
    const is_done = meter.classList.contains("complete");
    if (is_done) { return Promise.resolve(); }
    const outer = meter.querySelector(".outer")
    return queryProgress(simID, is_done)
        .then((info) => {
            console.log(info);
            if (info.is_done) {
                meter.classList.add("complete");
                meter.classList.remove("incomplete");
                if (info.cancelled || info.failed) {
                    meter.classList.add("fail");
                } else {
                    meter.classList.add("success");
                }
            }
            if (Object.hasOwn(info, "progress")) {
                if (info.progress[1] === 0) { return info; }
                outer.style.setProperty("--prog", `${100*info.progress[0]/info.progress[1]}%`);
            }
        })
        .catch((error) => {
            console.error(`Update sim selection progress error: ${error}`)
        });
}

function refreshSimulationSidebar() {
    // Clear all the current sim selections and remove from DOM
    const selections = simSidebar.querySelectorAll(".sim-selection-box");
    sim_selections = {};
    selections.forEach(selection => {
        selection.parentElement.removeChild(selection);
    });
    // Fetch sim history in backend DB
    fetch(apiURL("get_sims_history"))
    .then((response) => response.json())
    .then((infos) => {
        // Should be list of StartedSimulationInfo
        console.log(infos);
        infos.forEach(info => {
            const simID = info.sim_id;
            const config = info.config;
            if (!validID(simID)) {
                return info;
            }
            const newSelection = createSimSelection(config, simID);
            // Note: Check to store the simulation in sim_selections because
            // we only want running simulations in sim_selections.
            const meter = newSelection.querySelector(".radial-meter")
            if (info.is_done) {
                meter.classList.add("complete");
                meter.classList.remove("incomplete");
                if (info.cancelled || info.failed) {
                    meter.classList.add("fail");
                } else {
                    meter.classList.add("success");
                }
            } else {
                sim_selections[simID] = newSelection;
            }
            console.log(info);
        });
        return infos;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
}


// Turns the entry into a SimulationStartConfig data layout
function entryToConfig() {
    const name = configNameEntry.value;
    const key = configKeyEntry.value;
    const family = configFamilyEntry.value;
    const type = configTypeEntry.value;
    const kwargs = getKwargs(startPanel.querySelector(".kwarg-panel"));
    const config = {
        name: name,
        sim_key: key,
        sim_family: family,
        sim_type: type,
        kwargs: kwargs
    };
    return config;
}
function createSimSelection(config, simID) {
    const newSelection = prefabSimSelectBox.cloneNode(true);
    // Set up new selection box
    const selectionID = `${simID}`;
    newSelection.classList.remove("prefab");
    const label = newSelection.querySelector("label");
    const input = newSelection.querySelector(".sim-selection-checkbox")
    input.id            = selectionID;
    label.htmlFor           = selectionID;
    label.textContent   = config.name;
    simSidebar.appendChild(newSelection);
    // Set up cancel button
    const cancelButton = newSelection.querySelector(".cancel-sim-button");
    cancelButton.addEventListener("click", stopSimulationFromSelection.bind(null, newSelection));
    // Return selection box
    return newSelection;
}
function validID(simID) { return noID !== simID; }
function startSimulation() {
    // Read relevant information and gather kwargs
    const config = entryToConfig();
    fetch(apiURL("start-new-test"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
    })
    .then((response) => response.json())
    .then((info) => {
        console.log(info);
        const simID = info.id;
        if (!validID(simID)) {
            return info;
        }
        const newSelection = createSimSelection(config, simID);
        // Store new simulation in tracker
        sim_selections[simID] = newSelection;
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
}
function stopSimulationFromSelection(simSelection) {
    
    const input = simSelection.querySelector(".sim-selection-checkbox")
    const meter = simSelection.querySelector(".radial-meter")
    const outer = meter.querySelector(".outer")
    const simID = input.id;
    // Set stopping visuals and remove from sim_selections
    delete sim_selections[simID];
    meter.classList.add("cancelling");
    stopSimulation(simID)
        .then((response) => {
            console.log(`Done calling stop simulation on ${simID}`);
            
            updateSimSelectionProgress(simID, simSelection)
                .then((response) => {
                    // Put back in simSelection and stop cancellation visual
                    sim_selections[simID] = simSelection;
                    meter.classList.remove("cancelling");
                })
        })
        .catch((error) => {
            console.error(`Error while stopping simulation: ${error}`);
        });
}
// Sends the request to actually stop the given simulation
function stopSimulation(simID) {
    return controlStopSim(simID);
}


function setupKwargBoxes() {
    // Get kwarg boxes
    const kwargBoxes = document.querySelectorAll(".kwarg-panel");
    // Add listener to kwarg box add button
    for (const box of kwargBoxes) {
        const addKwargBtn = box.querySelectorAll(".add-kwarg");
        for (const btn of addKwargBtn) {
            console.log(`Adding event listener to btn ${btn}`);
            btn.addEventListener("click", addKwarg.bind(null, box));
        }
    }
}
function addKwarg(kwargPanel) {
    if (!kwargPanel.classList.contains("kwarg-panel")) {
        console.error(`Not adding kwarg because panel ${kwargPanel} is not a kwarg-panel.`);
        return;
    }
    const kwargArea = kwargPanel.querySelector(".kwarg-area");
    const newKwarg = prefabKwarg.cloneNode(true);
    newKwarg.classList.remove("prefab");
    // Setup listeners on new kwarg
    const removeBtn = newKwarg.querySelector(".remove-kwarg-btn");
    if (removeBtn !== null) {
        removeBtn.addEventListener("click", removeKwarg.bind(null, newKwarg));
    }
    kwargArea.appendChild(newKwarg);
}
function removeKwarg(kwargRow) {
    kwargRow.parentElement.removeChild(kwargRow);
}
function clearKwargBox(kwargPanel, deleteRows=false) {

}

setupKwargBoxes();


const fullResourcePreview = document.querySelector(".resource-preview.full-preview")
const miniResourcePreview = document.querySelector(".resource-preview.mini-preview")
resourceUsageDisplayUtils.setupResourceUsageDisplay(fullResourcePreview);
resourceUsageDisplayUtils.setupResourceUsageDisplay(miniResourcePreview, true);

tryBtn.addEventListener("click", getNumber);
testBtn.addEventListener("click", testNumberAPI);
resourceBtn.addEventListener("click", displayResourceUsage);
scalarDataTestBtn.addEventListener("click", displayScalarDataTest);
imageTestBtn.addEventListener("click", displayVideoTest);
startSimTestBtn.addEventListener("click", startSimTest);
queryProgressTestBtn.addEventListener("click", testQueryProgress);
stopSimTestBtn.addEventListener("click", stopSimTest);
fillHistoryTestBtn.addEventListener("click", refreshSimulationSidebar);


simTestTimestepsSlider.addEventListener("change", (e) => {
    testSimTimesteps = Number(e.target.value);
});


startSimBtn.addEventListener("click", startSimulation);



// Setup intervals
setInterval(updateAllSimSelectionProgress, defaultSimProgressUpdateInterval);


refreshSimulationSidebar();



function polyline(T, Y, tscale, yscale) {
    return T.map((t, i) => tscale(t).toFixed(1) + "," + yscale(Y[i]).toFixed(1)).join(
        " "
    );
}

function test() {
    const margin = {top: 30, right: 30, bottom: 30, left: 60};
    const n = 10;
    const x = d3.range(0, n);
    const y = x.map((t) => 0.5 * Math.pow(t, 1.5));

    const extentY = d3.extent(y);

    const width = 500;
    const height = 500;
    const svg = d3
        .select("body")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .style("border", "1px solid black");

    const xScale = d3
        .scaleLinear()
        .domain([x[0], x[x.length - 1]])
        .range([margin.left, width - margin.right]);
    const yScale = d3
        .scaleLinear()
        .domain(extentY)
        .nice()
        .range([height - margin.bottom, margin.top]);
    console.log("xScale: " + xScale);
    console.log("yScale: " + yScale);

    const xAxis = svg
        .append("g")
        .attr("transform", `translate(0,${margin.top})`)
        .call(d3.axisTop(xScale));
    const yAxis = svg
        .append("g")
        .attr("transform", `translate(${margin.left - 1}, 0)`)
        .call(d3.axisLeft(yScale));

    const pline = svg
        .append("polyline")
        .attr("fill", "none")
        .attr("stroke", "steelblue")
        .attr("stroke-width", 1.5)
        .attr("points", polyline(x, y, xScale, yScale));

    // d3.select("body").append("svg", svg.node());
}

test();


function plotVideosTest() {
    dataUtils.getAllNewImages()
        .then((results) => {
            console.log(results);
            const gif_src = mediaUtils.binaryToGIF(results);
            imageTestOut.src = gif_src;
        });
}
