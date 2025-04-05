import { apiURL } from "./api_link.js";

const dataUtils = (
    function() {
        const fetchAllRecentValues    = () => {return fetch(apiURL(`all-recent-scalars`));}
        const fetchAllRecentImages    = () => {return fetch(apiURL(`all-recent-images`));}
        // const fetchAllRecentValues    = () => {return fetch(apiURL(`read-key/?exp_key=${encodeURIComponent("tb\\stock\\train")}&key=${encodeURIComponent("rollout/ep_rew_mean")}&recent=True`));}

        // Public Utilities
        const getAllNewScalars = function() {
            return fetchAllRecentValues()
                .then((response) => {
                    console.log(response);
                    return response.json();
                });
        }
        const getAllNewImages = function() {
            return fetchAllRecentImages()
                .then((response) => {
                    const buff = response.arrayBuffer();
                    console.log(buff);
                    return buff;
                });
        }

        return {
            getAllNewScalars,
            getAllNewImages
        };
    }
)();

export { dataUtils };