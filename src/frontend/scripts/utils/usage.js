// const resourceUsageUtils = (
//     function() {
//         const fetchResourceUsageDetailed    = () => {return fetch("http://127.0.0.1:8000/get-usage-detailed");}
//         const fetchResourceUsageSimple      = () => {return fetch("http://127.0.0.1:8000/get-usage-simple");}

//         const getResourceUsageDetailed = function() {
//             return fetchResourceUsageDetailed()
//                 .then((response) => {
//                     return response.json();
//                 });
//         }

//         const getResourceUsageSimple = function() {
//             return fetchResourceUsageSimple()
//                 .then((response) => {
//                     return response.json();
//                 });
//         }

//         return { getResourceUsageDetailed, getResourceUsageSimple };
//     }
// )();


// export { resourceUsageUtils };

const testUtils = (
    function() {
        const testLog = function() {
            console.log("Logging test function");
        }

        return { testLog };
    }
)();

export { testUtils };