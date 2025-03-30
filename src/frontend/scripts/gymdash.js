import { resourceUsageUtils } from "./utils/usage.js";
import { apiURL } from "./utils/api_link.js";

const tryBtn        = document.querySelector("#try-api-btn");
const tryBtnOut     = document.querySelector("#try-api-out");
const testBtn       = document.querySelector("#test-api-btn");
const testBtnOut    = document.querySelector("#test-api-out");
const resourceBtn       = document.querySelector("#resource-usage-btn");
const resourceBtnOut    = document.querySelector("#resource-usage-out");

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

tryBtn.addEventListener("click", getNumber);
testBtn.addEventListener("click", testNumberAPI);
resourceBtn.addEventListener("click", displayResourceUsage);





