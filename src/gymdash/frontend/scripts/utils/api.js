const apiAddr = "<<api_addr>>";
const apiPort = "<<api_port>>";

function _apiURL() {
    return apiAddr + ":" + apiPort;
}
function apiURL(api_subaddr) {
    return _apiURL() + "/" + api_subaddr;
}
export { apiURL };