# Polaris Blueprint Application

## Overview

This repository presents a simple yet instructive example of an application that can be used as a
template for new applications. It includes best practices for:

- Structuring a multi-tier application of an Angular or React frontend with a Node backend.
- Unit Testing
- E2E Testing
- CI/CD pipeline
- Linting and Formatting
- Deploying to OSS2

Polaris is using `PolarisMetadata.json` for analytical purposes, please do NOT remove this file as
it helps us improve Polaris for everyone.

## Getting Started

See
[How to Start](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/How-to-Start.aspx)
for a comprehensive guide on how to get started creating a new project from this template.

A VS Code Remote Development set up is the recommended development environment. Details can be found
[here](.devcontainer/README.md).

#### A Cheat Sheet on getting started:

- Quickstart guide for configuring the repository for a
  [quick UI deployment](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/Polaris---UI-Deploy-Quickstart.aspx).
- Most github workflows will fail until you configure the
  [OSS2_PAT_TOKEN](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/How-to-Start.aspx#add-the-oss2_pat_token-secret)
  repo secret. PAT tokens are needed to give workflows/actions access to the source repository.
- The bare minimum to getting a
  [deploy to OSS2](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/How-to-Start.aspx#step-3.-setup-oss-2.0-application)
  is to configure the OSS2 app and namespace, add relevant keys to the repo, and set the env var
  IS_VAULT_INTEGRATED=false, and run a deploy. You don't need a datastore, okta, calico etc to look
  at the UI.
- If your dev environment is configured correctly, and you have an API server and an Angular UI, for
  example, then the following two commands can be run to have an end-to-end system running locally.
  - `npm run start:api` to start the backend
  - `npm run start:ui` to start the UI

## Further Information

Please refer to these documentation
[Running Polaris Blueprint Application Locally](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/Running-Polaris-Blueprint-Application-Locally.aspx)

## Getting Help

Please refer to this documentation
[FAQ documentation](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/Polaris--Launchpad---FAQs.aspx)

## Getting Involved

You can join Polaris Teams channel
[here](https://teams.microsoft.com/l/team/19%3AsH5pJK4UVvlLmf-reLnBolhLL_5S34y1RHBEVq0aKTk1%40thread.tacv2/conversations?groupId=c037e643-6e27-4f22-88e3-d653eaf62bdb&tenantId=2a6e6092-73e4-4752-b1a5-477a17f5056d)
<br> And you can contact us here
[MMC GL PolarisContactUs](mailto:#MMC%20GL%20PolarisContactUs%20%3C#MMCGLPolarisContactUs@mmc.com%3E)

## Who We Are

Please refer to this documentation
[Polaris Team Contributors and Collaborators](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/Polaris-Team---Contributors-and-Collaborators.aspx)

## Contributing

Contributions are welcome - please see [CONTRIBUTING.md](CONTRIBUTING.md) <br> Also please refer to
this documentation
[Polaris Contributing](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/Polaris--Schematics-Approach.aspx)

## Discover More About Polaris

For Polaris guides, tutorials and technical documentation please visit
[Polaris SharePoint Page](https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/Polaris.aspx)
