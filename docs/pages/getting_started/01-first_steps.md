# First Steps
## Running Locally
### Launch GymDash
```bash
# This creates '.gymdash-projects' folder in the launching folder
# and starts a frontend HTTP server and a backend API server.
python -m gymdash.start
```
For additional launch options, see the [Appendix - Other Launch Options](#other-launch-options).

### Navigation
Navigate your web browser to your `localhost` port `8888`: `http://127.0.0.1:8888/src/gymdash/frontend/`. This loads the HTML page used to interact with your GymDash project.

### Launch Options
| Argument | Arg | Default | Description |
| --- | --- | --- | --- |
| project-dir | -d | `./.gymdash-projects` | Set the directory for the gymdash project. This will create the necessary folders in the project. |folder.
| port        | -p | `8888` | Port for the frontend interface. The number you use to access the GymDash web interface, e.g. `localhost:<--port>/src/gymdash.frontend/`.
| apiport     | -b | `8887` | Port for the API server. The frontend should automatically adapt to query on the given port for API calls.
| apiaddr     | -a | `127.0.0.1` | **UNTESTED!** Default is same as `localhost`. This should be the IP address upon which the backend server runs.
| apiworkers  | -w | `1` | Number of API server workers. This is the number of workers set ONLY for the Uvicorn server, not for any of the simulation work that may launch.
| apiserver   | -  | `dev` | The locality of the launched frontend server. Can be one of `dev`, `lan`, or `custom_ip`. On `dev`, only `localhost` (`127.0.0.1`) will be useable. On `lan` local IPs on the same network (usually `192.168.x.x`). On `custom_ip`, the IP in `apiserver-ip` is used.
| apiserver-ip| -  | `127.0.0.1` | - |
| no-frontend | -  | - | Launch only the backend API server. |
| no-backend  | -  | - | Launch only the frontend HTTP server. |

[Next: Page Controls](02-controls.md)