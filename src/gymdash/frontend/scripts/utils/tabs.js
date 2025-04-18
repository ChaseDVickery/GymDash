
// https://www.w3schools.com/howto/howto_js_tabs.asp
function openTab(evt, tabID) {
    // Declare all variables
    var i, tabcontent, tablinks;

    // Hide all tabs
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].classList.add("hidden");
    }
    // Show the current tab
    document.getElementById(tabID).classList.remove("hidden");

    // Remove "active" from all tablinks
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    // Add "active" to the correct tab link
    for (const tablink of tablinks) {
        console.log(tablink);
        if (tablink.dataset.tab === tabID) {
            tablink.classList.add("active");
            break;
        }
    }
}