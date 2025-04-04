import { apiURL } from "./api_link.js";

const dataUtils = (
    function() {
        const fetchAllRecentValues    = () => {return fetch(apiURL(`read-key/?exp_key=${encodeURIComponent("tb\\stock\\train")}&key=${encodeURIComponent("rollout/ep_rew_mean")}&recent=True`));}

        // Public Utilities
        const getAllNewScalars = function() {
            return fetchAllRecentValues()
                .then((response) => {
                    return response.json();
                });
        }

        return {
            getAllNewScalars
        };
    }
)();

export { dataUtils };