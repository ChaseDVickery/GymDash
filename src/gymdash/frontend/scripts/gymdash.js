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
        sim_key: "stable_baselines/ppo",
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

function testQueryProgress() {
    const simulationQuery = {
        id: "dummy_id",
        timeout: 0.0,
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


simTestTimestepsSlider.addEventListener("change", (e) => {
    testSimTimesteps = Number(e.target.value);
});


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

// test();


function plotVideosTest() {
    dataUtils.getAllNewImages()
        .then((results) => {
            console.log(results);
            const gif_src = mediaUtils.binaryToGIF(results);
            imageTestOut.src = gif_src;
        });
}
