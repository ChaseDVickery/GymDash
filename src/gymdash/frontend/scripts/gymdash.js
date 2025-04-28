import { resourceUsageUtils, resourceUsageDisplayUtils } from "./utils/usage.js";
import { dataUtils } from "./utils/data.js";
import { vizUtils } from "./utils/viz.js";
import { mediaUtils } from "./utils/media_utils.js";
import { apiURL } from "./utils/api_link.js";

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
const deleteAllSimsTestBtn = document.querySelector("#delete-all-sims-test-btn");
const deleteSelectedSimsTestBtn = document.querySelector("#delete-selected-sims-test-btn");



// Constants
const defaultSimProgressUpdateInterval = 2000;  // (ms)
const defaultTimeout = 0.5; // (s)
const noID = "00000000-0000-0000-0000-000000000000"; // (str(UUID))

// Structures
// sim_selections store information
let sim_selections = {};
// allData stores all the data retrieved from the backend
// Maps in the following way:
//      simID -> {
//          "scalars" -> {stat_key1_s -> [], ...},
//          "images" -> {stat_key1_i -> [], ...},
//          "audio" -> {stat_key1_a -> [], ...}
//      }
let allData = {};

// Sidebar
const simSidebar = document.querySelector(".sim-selection-sidebar");
const deselectAllBtn            = simSidebar.querySelector("#deselect-all-btn");
const selectAllBtn              = simSidebar.querySelector("#select-all-btn");
// Control
const startPanel                = document.querySelector("#start-panel");
const controlColumn             = document.querySelector(".control-column");
const controlPanel              = document.querySelector("#control-panel");
const controlResponsePanel      = document.querySelector("#control-response-panel");
const queryColumn               = document.querySelector(".query-column");
const queryPanel                = document.querySelector("#query-panel");
const queryResponsePanel        = document.querySelector("#query-response-panel");
const configNameEntry           = startPanel.querySelector("#config-name1");
const configKeyEntry            = startPanel.querySelector("#config-key1");
const configFamilyEntry         = startPanel.querySelector("#config-family1");
const configTypeEntry           = startPanel.querySelector("#config-type1");
const startSimBtn               = startPanel.querySelector("#start-sim-btn");
const queueSimBtn               = startPanel.querySelector("#queue-sim-btn");
const sendControlBtn            = document.querySelector("#send-control-btn");
const sendQueryBtn              = document.querySelector("#send-query-btn");

// Plots
const plotArea                  = document.querySelector("#plots-area");
// Multimedia Panel
const mmInstancePanel           = document.querySelector(".media-panel");
const mmImageSubmediaArea       = mmInstancePanel.querySelector("#image-panel > .media-instance-area");
const mmAudioSubmediaArea       = mmInstancePanel.querySelector("#audio-panel > .media-instance-area");
const mmVideoSubmediaArea       = mmInstancePanel.querySelector("#video-panel > .media-instance-area");



// Prefabs
const prefabSimSelectBox        = document.querySelector(".prefab.sim-selection-box");
const prefabKwargPanel          = document.querySelector(".prefab.kwarg-panel");
const prefabKwarg               = document.querySelector(".prefab.kwarg");
const prefabImageMedia          = document.querySelector(".prefab.multimedia-instance-panel.image-instance-panel");
const prefabAudioMedia          = document.querySelector(".prefab.multimedia-instance-panel.audio-instance-panel");
const prefabVideoMedia          = document.querySelector(".prefab.multimedia-instance-panel.video-instance-panel");
const prefabResizerBar          = document.querySelector(".prefab.resizer-bar");
const prefabcontrolRequestBox   = document.querySelector(".prefab.control-request");
prefabSimSelectBox.remove();
prefabKwargPanel.remove();
prefabKwarg.remove();
prefabImageMedia.remove();
prefabAudioMedia.remove();
prefabVideoMedia.remove();
prefabResizerBar.remove();
prefabcontrolRequestBox.remove();

const testImageOutputs = []

let testSimTimesteps = Number(simTestTimestepsSlider.value)

function call_random() {
    return fetch(apiURL("random"));
    // return fetch(apiURL("big-data1000");
    // return fetch(apiURL("big-data100000");
    // return fetch(apiURL("big-data1000000");
}

function getActiveSelections() {

}
function getSimName(simIDorSelection) {
    if (typeof simIDorSelection === "string") {
        const selections = getAllSelections();
        if (Object.hasOwn(getAllSelections(), simIDorSelection)) {
            return selections[simIDorSelection].querySelector("label").textContent;
        }
    } else {
        return simIDorSelection.querySelector("label").textContent;
    }
}
/**
 * Return a mapping from all simulation selection IDs to the simulation
 * selection nodes.
 * 
 * @returns Object mapping each simulation ID to the selection object
 */
function getAllSelections() {
    const mapping = Array.from(document.querySelectorAll(".sim-selection-checkbox")).reduce(
        (curr_map, curr_chkbox) => {
            curr_map[curr_chkbox.id] = curr_chkbox.parentElement.parentElement;
            return curr_map;
        },
        {}
    )
    return mapping;
}
/**
 * Return a mapping from each selected simulation ID to the selected
 * selection object.
 * 
 * @returns Object mapping each selected simulation ID to the selection object.
 */
function getSelectedSelections() {
    const mapping = Array.from(document.querySelectorAll(".sim-selection-checkbox")).reduce(
        (curr_map, curr_chkbox) => {
            if (curr_chkbox.checked) {
                curr_map[curr_chkbox.id] = curr_chkbox.parentElement.parentElement;
            }
            return curr_map;
        },
        {}
    )
    return mapping;
}
function getSelectedData() {
    const selectedSelections = getSelectedSelections();
    const selectedData = {};
    for (const id in selectedSelections) {
        selectedData[id] = allData[id];
    }
    return selectedData;
}
function forEachSelection(doThis) {
    const selections = getAllSelections();
    for (const simID in selections) {
        doThis(selections[simID]);
    }
}
function selectAll() {
    forEachSelection((selection) => {
        const input = selection.querySelector(".sim-selection-checkbox")
        input.checked = true;
    })
}
function deselectAll() {
    forEachSelection((selection) => {
        const input = selection.querySelector(".sim-selection-checkbox")
        input.checked = false;
    })
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
    // dataUtils.getAllNewImages()
    //     .then((mediaReport) => {
    //         console.log(`mediaReport for ${mediaReport.simID}: ${mediaReport}`);
    //         for (let i = 0; i < mediaReport.media["image/gif"].length; i++) {
    //             setImageOutput(i, results[i]);
    //         }
    //     })
    //     .catch((error) => {

    //     });



    // const selectionOptions = document.querySelectorAll(".sim-selection-checkbox");
    // const randomSelection = selectionOptions[Math.floor(Math.random()*selectionOptions.length)];
    // const simID = randomSelection.id;
    // console.log(`Getting new media for random selection: ${simID}`);
    // dataUtils.getSimNewMedia(simID)
    //     .then((mediaReport) => {
    //         console.log(`mediaReport for ${mediaReport.simID}: ${mediaReport}`);
    //         console.log(mediaReport.media["image/gif"]);
    //         for (let i = 0; i < mediaReport.media["image/gif"].length; i++) {
    //             console.log(mediaReport.media["image/gif"][i]);
    //             setImageOutput(i, mediaReport.media["image/gif"][i].url);
    //         }
    //     })
    //     .catch((error) => {

    //     });


    // const selectionOptions = document.querySelectorAll(".sim-selection-checkbox");
    // const randomSelection = selectionOptions[Math.floor(Math.random()*selectionOptions.length)];
    // const simID = randomSelection.id;
    // console.log(`Getting new media for random selection: ${simID}`);
    // dataUtils.getRecent(simID, [], [], true)
    //     .then((mediaReport) => {
    //         console.log("Got media report.");
    //         console.log(mediaReport);
    //     })
    //     .catch((error) => {

    //     });


    updateData()
        .then((allDataReports) => {
            createPlots();
        });
}


function updateData() {
    // const selectionOptions = document.querySelectorAll(".sim-selection-checkbox");
    // const randomSelection = selectionOptions[Math.floor(Math.random()*selectionOptions.length)];
    // const simID = randomSelection.id;
    const dataRetrievalPromises = [];
    const allDataReports = [];
    const selectionOptions = document.querySelectorAll(".sim-selection-checkbox");
    for (let i = 0; i < selectionOptions.length; i++) {
        const simID = selectionOptions[i].id;
        console.log(`Getting new data for sim: ${simID}`);
        dataRetrievalPromises.push(
            dataUtils.getAll(simID, [], [], true)
            // dataUtils.getRecent(simID, [], [], true)
                .then((dataReport) => {
                    console.log("Got data report.");
                    console.log(dataReport);
                    allDataReports.push(dataReport);
                    return Promise.resolve(dataReport);
                })
                .catch((error) => {
                    console.error("Problem updating data for simulation " + simID + ". Returning promise of empty data report");
                    return Promise.resolve(new dataUtils.DataReport(simID));
                })
        );
    }
    return Promise.all(dataRetrievalPromises)
        .then((allDataReports) => {
            // Add the data from each new report to the current
            // allData report
            for (let j = 0; j < allDataReports.length; j++) {
                const simID = allDataReports[j].simID;
                if (!Object.hasOwn(allData, simID)) {
                    // allData[simID] = dataUtils.createEmptyDataReport(simID);
                    allData[simID] = new dataUtils.DataReport(simID);
                }
                // dataUtils.dataReportUnion(allData[simID], allDataReports[j]);
                allData[simID].addDataReport(allDataReports[j]);
            }
            console.log("ALL DATA");
            console.log(allData);
            return Promise.resolve(allDataReports);
        })
        .catch((error) => {
            console.error(`Error processing all data reports: ${error}`)
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

function createQueryBody(simID, timeout=defaultTimeout) {
    return {
        id: simID,
        timeout: timeout
    };
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
    return fetch(apiURL("cancel-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(q),
    }).then((response) => { return response.json(); });
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
    // Try JSON parsing or Just return the trimmed value
    else {
        try {
            return JSON.parse(valueString);
        } catch (e) {
            return valueString;
        }
    }
}
/**
 * Gathers all keyword arguments from input kwarg panel into a single
 * kwarg object.
 */
function getKwargs(elementWithKwargPanel) {
    const kwargArea = elementWithKwargPanel.querySelector(".kwarg-area");
    const allKwargEntries = kwargArea.querySelectorAll(".kwarg");
    const kwargs = {};
    for (const kwargEntry of allKwargEntries) {
        // Only include if kwarg is a DIRECT DESCENDENT of this kwarg panel
        if (kwargEntry.parentElement !== kwargArea) { continue; }
        // Get key and value for kwarg
        let key = kwargEntry.querySelector(".key").value.trim();
        let val = kwargEntry.querySelector(".value").value.trim();
        let subkwargsPanel = kwargEntry.querySelector(".kwarg-subkwargs").querySelector(".kwarg-panel");
        if (key === "") { continue; }
        if (val === "") { val = true; }
        const splitKey = key.split(/\s+/);
        key = splitKey.join("_");
        // If we have subkwargs, use those instead of value
        if (subkwargsPanel !== null) {
            val = getKwargs(subkwargsPanel);
        } else {
            val = convertKwargValue(val);
        }
        kwargs[key] = val;
    }
    console.log("KWARGS");
    console.log(kwargs);
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
    const selections = getAllSelections();
    const selected = getSelectedSelections();
    for (const id in selections) {
        selections[id].remove();
    }
    sim_selections = {};
    // Fetch sim history in backend DB
    fetch(apiURL("get-sims-history"))
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
            const startChecked = Object.hasOwn(selected, simID);
            const newSelection = createSimSelection(config, simID, startChecked);
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

function sendSingleQuery(simID) {
    // Gather kwargs
    const kwargs = getKwargs(controlColumn.querySelector(".kwarg-panel"));
    // Create and send custom query
    const queryBody = createQueryBody(simID);
    queryBody.custom_query = {triggered: true, value: kwargs};
    return query(queryBody);
}
function sendQuery() {
    const selections = getSelectedSelections();
    const promises = [];
    for (const simID in selections) {
        promises.push(sendSingleQuery(simID));
    }
    Promise.all(promises)
        .then((queryInfos) => {
            console.log("QUERY INFOS:");
            console.log(queryInfos);
        })
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
function createSimSelection(config, simID, startChecked=true) {
    const newSelection = prefabSimSelectBox.cloneNode(true);
    // Set up new selection box
    const selectionID = `${simID}`;
    newSelection.classList.remove("prefab");
    const label = newSelection.querySelector("label");
    const input = newSelection.querySelector(".sim-selection-checkbox")
    input.id            = selectionID;
    input.checked       = startChecked;
    label.htmlFor       = selectionID;
    label.textContent   = config.name;
    simSidebar.appendChild(newSelection);
    // Set up cancel button
    const cancelButton = newSelection.querySelector(".cancel-sim-button");
    cancelButton.addEventListener("click", stopSimulationFromSelection.bind(null, newSelection));
    // Return selection box
    return newSelection;
}
function validID(simID) { return noID !== simID; }
function queueSimulation() {
    // Read relevant information and gather kwargs
    const config = entryToConfig();
    fetch(apiURL("queue-new-sim"), {
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

function showDeleteAllSimulationsOption() {
    deleteAllSimulations();
}
function deleteAllSimulations() {
    // Visually indicate all running sims as cancelling
    for (const [key, simSelection] of Object.entries(sim_selections)) {
        const meter = simSelection.querySelector(".radial-meter")
        const simID = key;
        // Set stopping visuals and remove from sim_selections
        delete sim_selections[simID];
        meter.classList.add("cancelling");
    }
    fetch(apiURL("delete-all-sims"))
        .then((response) => { return response.json(); })
        .then((info) => {
            sim_selections = {};
            allData = {};
            refreshSimulationSidebar();
        })
        .catch((error) => { console.error(`Error while deleting all simulations: ${error}`)});
}
function deleteSelectedSimulations() {
    console.log("deleteSelectedSimulations");
    // Visually indicate all running sims as cancelling
    const simIDs = [];
    for (const [key, simSelection] of Object.entries(getAllSelections())) {
        const checkbox = simSelection.querySelector(".sim-selection-checkbox");
        const meter = simSelection.querySelector(".radial-meter")
        const simID = key;
        if (checkbox.checked) {
            simIDs.push(simID);
            // Set stopping visuals and remove from sim_selections
            delete sim_selections[simID];
            meter.classList.add("cancelling");
            console.log("deleting " + simID);
        }
    }
    deleteSimulations(simIDs);
}
function deleteSimulations(simIDs) {
    console.log("SIM IDS");
    console.log(simIDs);
    fetch(apiURL("delete-sims"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ids: simIDs}),
    })
    .then((response) => { return response.json(); })
    .then((info) => {
        sim_selections = {};
        allData = {};
        refreshSimulationSidebar();
    })
    .catch((error) => { console.error(`Error while deleting all simulations: ${error}`)});
}


function setupKwargBox(kwargPanel) {
    const addKwargBtn = kwargPanel.querySelectorAll(".add-kwarg");
    for (const btn of addKwargBtn) {
        console.log(`Adding event listener to btn ${btn}`);
        btn.addEventListener("click", addKwarg.bind(null, kwargPanel));
    }
}
function setupKwargBoxes() {
    // Get kwarg boxes
    const kwargBoxes = document.querySelectorAll(".kwarg-panel");
    // Add listener to kwarg box add button
    for (const box of kwargBoxes) {
        setupKwargBox(box);
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
    const addSubkwargBtn = newKwarg.querySelector(".add-subkwarg-btn");
    if (addSubkwargBtn !== null) {
        addSubkwargBtn.addEventListener("click", addSubkwargs.bind(null, newKwarg));
    }
    kwargArea.appendChild(newKwarg);
}
function removeKwarg(kwargRow) {
    kwargRow.parentElement.removeChild(kwargRow);
}
function addSubkwargs(kwargRow) {
    const subkwargArea = kwargRow.querySelector(".kwarg-subkwargs");
    const newSubkwargs = prefabKwargPanel.cloneNode(true);
    setupKwargBox(newSubkwargs);
    subkwargArea.appendChild(newSubkwargs);
}
function clearKwargBox(kwargPanel, deleteRows=false) {

}

function updateControlRequestQueue(requests_model) {
    const requests = requests_model.requests;
    const selections = getAllSelections();
    for (const simID in requests) {
        const selection = selections[simID];
        for (const channel_key in requests[simID]) {
            console.log(requests[simID]);
            console.log(requests[simID][channel_key]);
            for (const request of requests[simID][channel_key]) {
                const requestBox = prefabcontrolRequestBox.cloneNode(true);
                requestBox.textContent = `sim='${getSimName(selection)}'(${simID}), channel='${request.key}', details='${request.details}'.`;
                controlResponsePanel.appendChild(requestBox);
            }
        }        
    }
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
deleteAllSimsTestBtn.addEventListener("click", showDeleteAllSimulationsOption);
deleteSelectedSimsTestBtn.addEventListener("click", deleteSelectedSimulations);


simTestTimestepsSlider.addEventListener("change", (e) => {
    testSimTimesteps = Number(e.target.value);
});

// Listening for control requests sent from server
const ctrlReqSrc = new EventSource(apiURL("get-control-requests"));
ctrlReqSrc.onopen = () => {
    console.log("EventSource connected");
}
ctrlReqSrc.addEventListener("retrieval", (event) => {
    const requests = JSON.parse(event.data);
    console.log("EventSource REQUESTS");
    console.log(requests);
    updateControlRequestQueue(requests);
});

deselectAllBtn.addEventListener("click", deselectAll);
selectAllBtn.addEventListener("click", selectAll);
startSimBtn.addEventListener("click", startSimulation);
queueSimBtn.addEventListener("click", queueSimulation);
sendControlBtn.addEventListener("click", sendQuery);
sendQueryBtn.addEventListener("click", sendQuery);


// Setup intervals
setInterval(updateAllSimSelectionProgress, defaultSimProgressUpdateInterval);


refreshSimulationSidebar();
openTab(null, "tab-analyze");

function clearMainPlot() {
    const svgs = plotArea.querySelectorAll("svg");
    for (let i = 0; i < svgs.length; i++) {
        plotArea.removeChild(svgs[i]);
    }
}
function clearMediaPanel() {
    const submediaAreas = document.querySelectorAll(".media-instance-area");
    for (let i = 0; i < submediaAreas.length; i++) {
        const mmInstancePanels = submediaAreas[i].querySelectorAll(".multimedia-instance-panel");
        for (const mmip of mmInstancePanels) {
            submediaAreas[i].removeChild(mmip);
        }
    }
}
function showMMInstance(simID, type, datum) {
    let panel;
    if (type === dataUtils.DataReport.IMAGE) {
        panel = prefabImageMedia.cloneNode(true);
        mmImageSubmediaArea.appendChild(panel);
    }
    else if (type === dataUtils.DataReport.AUDIO) {
        panel = prefabAudioMedia.cloneNode(true);
        mmAudioSubmediaArea.appendChild(panel);
    }
    else if (type === dataUtils.DataReport.VIDEO) {
        panel = prefabVideoMedia.cloneNode(true);
        mmVideoSubmediaArea.appendChild(panel);
    }
    if (!panel) { return panel; }
    const mediaArea = panel.querySelector(".media-area");
    mediaArea.firstElementChild.src = datum.value;
    const caption = panel.querySelector(".media-info");
    const simSelection = getAllSelections()[simID];
    caption.textContent = `sim: ${getSimName(simSelection)}`;
    return panel;
}
function displayMMIData(mmiData) {
    console.log("display mmi data");
    console.log(mmiData);
    clearMediaPanel();
    const data = mmiData.getData();
    for (const datapoint of data) {
        const newInstancePanel = showMMInstance(datapoint.simID, datapoint.type, datapoint.datum);
    }
}
function onClickMMI(d) {
    const mmiData = d3.select(d.target).data()[0];
    displayMMIData(mmiData);
}
function createPlots() {
    // const key = "rollout/ep_rew_mean";
    const key = "my_number";

    clearMainPlot();

    const selectedData = getSelectedData();

    let svg = vizUtils.createLinePlotForKey(key, selectedData);

    const condense = true;
    vizUtils.addAllMMIs(selectedData, svg, onClickMMI, condense);

    // vizUtils.addAllMMIs(allData, svg, onClickMMI);

    // const createdMMIs = vizUtils.addMMIs("episode_video_thumbnail", allData, svg, onClickMMI);
    // vizUtils.addMMIs("episode_video", allData, svg, onClickMMI, createdMMIs);
    
    d3.select("#plots-area").append(() => svg.node());
}


addResizeBar(plotArea, "ew");
addResizeBar(startPanel);
// addResizeBar(controlColumn);
addResizeBar(queryColumn, "ew", "before");
// addResizeBar(queryColumn, "ew", "after");
// queryPanel

// Adapted from:
// https://stackoverflow.com/questions/8960193/how-to-make-html-element-resizable-using-pure-javascript
function addResizeBar(resizablePanel, direction="ew", position="after") {
    var startX, startY, startWidth, startHeight;
    const newBar = prefabResizerBar.cloneNode(true);
    newBar.classList.add(direction);
    if (position === "after") {
        resizablePanel.after(newBar);
    } else if (position === "before") {
        resizablePanel.before(newBar);
    }

    // var resizer = document.querySelector(".resizer-bar");
    // var p = plotArea;
    function initDrag(e) {
        startX = e.clientX;
        startY = e.clientY;
        startWidth = parseInt(document.defaultView.getComputedStyle(resizablePanel).width, 10);
        startHeight = parseInt(document.defaultView.getComputedStyle(resizablePanel).height, 10);
        document.documentElement.addEventListener('mousemove', doDrag, false);
        document.documentElement.addEventListener('mouseup', stopDrag, false);
    }
    
    function doDrag(e) {
        if (direction === "ew") {
            const change = e.clientX;
            if (position === "after") {
                resizablePanel.style.width = (startWidth + change - startX) + 'px';
            } else {
                resizablePanel.style.width = (startWidth + startX - change) + 'px';
            }
            
        } else if (direction === "ns") {
            const change = e.clientY;
            if (position === "after") {
                resizablePanel.style.height = (startHeight + change - startY) + 'px';
            } else {
                resizablePanel.style.height = (startHeight + startY - change) + 'px';
            }
        }
       
    //    p.style.height = (startHeight + e.clientY - startY) + 'px';
    }
    
    function stopDrag(e) {
        document.documentElement.removeEventListener('mousemove', doDrag, false);
        document.documentElement.removeEventListener('mouseup', stopDrag, false);
    }

    // var p = document.querySelector('.media-panel'); // element to make resizable
    

    newBar.addEventListener('mousedown', initDrag, false);

    // resizer.addEventListener('click', function init() {
    //     p.removeEventListener('click', init, false);
    //     p.className = p.className + ' resizable';
    //     // var resizer = document.createElement('div');
    //     // resizer.className = 'resizer';
    //     // p.appendChild(resizer);
    //     resizer.addEventListener('mousedown', initDrag, false);
    //     // resizer.style.minWidth = "50px";
    //     // resizer.style.width = "50px";
    //     // resizer.style.flex = "1 1 50px";
    // }, false);
}