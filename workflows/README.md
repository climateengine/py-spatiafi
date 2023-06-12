# Build Workflows

Building is done by [Argo Workflows](https://argoproj.github.io/argo-workflows/) and [Argo Events](https://argoproj.github.io/argo-events/)
is (optionally) used to automatically trigger builds when new commits are pushed to the repository.

  - [py-spfi-api-build-wf.yaml](py-spfi-api-build-wf.yaml) -
    This is the `Workflow` definition.  Here you can define the steps to build the project.
    In its simplest form, it can call an existing `WorkflowTemplate`  (more on this later).
  - [repo-sensor.yaml](repo-sensor.yaml) - This defines the "Sensor" which will watch for changes to GitHub and
    trigger the [py-spfi-api-build-wf.yaml](py-spfi-api-build-wf.yaml) `Workflow`
    when a new commit is pushed to the repository.
  - [kustomization.yaml](kustomization.yaml) - This is the `Kustomization` definition.  It helps deploy the `Workflow`
    and `Sensor` objects to the cluster.
  - [deploy-sensor.sh](delpoy-sensor.sh) - This is a helper script to deploy the `Workflow` and `Sensor` to the cluster.
    This should be run once to deploy the `Workflow` and `Sensor` to the cluster - enabling automatic builds.
  - [submit-wf.sh](submit-wf.sh) - This is a helper script to submit the `Workflow` to the cluster.
    This can be run at any time to manually trigger a build.

## Workflow Templates

There are a number of predefined `WorkflowTemplate`s. These are shared across all projects.
`WorkflowTemplate`s can be viewed in the [Argo Workflows Web UI](https://builder.climateengine.net/workflow-templates/argo)
and are defined in https://github.com/climateengine/ce-argo-workflows-deploy/tree/main/ce-builder/argo-workflows/workflow-templates
