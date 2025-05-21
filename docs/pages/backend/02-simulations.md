# Simulations
The backbone (and entire functionality) of GymDash revolves around the `Simulation`. Simulations are just an abstraction that is wrapped around any kind of process that can be run, stopped, and interacted with. The initial intention is to have Simulations wrap long-running processes like machine learning, but they also work for more arbitrary simulations.

## Simulation Class
`Simulations`

When the backend is restarted, there is currently no way to "restart" a `Simulation`, thought the "restart" is a work in progress. Instead, it does do a minimal setup to allow data streaming

How to access project-wide and simulation-specific resource folders.


## Template Examples:
### Stable Baselines
StableBaselinesSimulation
Example:
stable_baselines
### Machine Learning (PyTorch)
MLSimulation
Example:
example_ml
### Interactive Simulation
CustomControlSimulation
Example:
custom_control


### Simulations
