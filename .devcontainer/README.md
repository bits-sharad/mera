# Remote Development

- [Remote Development](#remote-development)
  - [Motivations](#motivations)
  - [Setup](#setup)
  - [Running remote dev for a project](#running-remote-dev-for-a-project)
  - [Security scanning](#security-scanning)
    - [GitGuardian Integration](#gitguardian-integration)
  - [Testing](#testing)
    - [Unit Tests](#unit-tests)
    - [End-to-end API Tests](#end-to-end-api-tests)
  - [Troubleshooting](#troubleshooting)
    - [Network issues](#network-issues)
  - [Tips](#tips)

See <https://code.visualstudio.com/docs/remote/remote-overview> for an overview of VS Code's remote
development.

The documentation for the Remote Container VS Code extension suggests that Docker Desktop must be
installed. Docker Desktop is not required. This page covers installing Docker CE with the Docker
Compose CLI plugin.

Running with Docker Desktop, without WSL2 is also an option for a remote dev environment. It will be
a slower dev experience though.

Work is underway for MGTI to support a VS Code/WSL2/Docker CE configuration that can be installed to
developer machines.

## Motivations

1. Use a docker image for the common, static dev dependencies, e.g. node + cypress
1. Keep all project files outside of the container so that the image does not need to be rebuilt
1. Use WSL and Docker CE so that it performs well
1. Avoid the need to use a licensed version of Docker Desktop

## Setup

For guidance on setting up your development environment, Polaris provides a customized WSL
distribution containing all the necessary libraries to kickstart your setup in just a few minutes.
Refer to the documentation available at
<https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/WSL--Create-your-development-Environment.aspx>
for more details.

## Running remote dev for a project

1. Open WSL
2. cd ~
3. mkdir code && cd code
4. Clone this repository from the command line
5. cd into the cloned project root folder
6. Run

   ```sh
   code .
   ```

7. Open the Remote dev container
8. Your project root in wsl will be mapped to /home/build/app
9. Open a terminal ( ctrl-shift-' ) run "npm install"

## Security scanning

### Gitguardian Integration

To enhance the security of your applications, we recommend integrating Gitguardian into your
containerized development environment. Gitguardian is a powerful tool that helps prevent the
accidental exposure of sensitive information in your codebase.

- DevContainer ships with ggshield cli tool used to prevent secret from commiting to github

- Create a file called `.container_env` on the root of your polaris based project.

- Generate an API key by following the documentation provided
  [here](https://mmcglobal.sharepoint.com/sites/GIS-DevSecOps-SecureSDLC/SitePages/Authenticate-GGShield.aspx#follow-the-steps-below-to-authenticate-by-storing-the-api-token-as-an-environment-variable).
  Save the API key as a secret in the .container_env file using the following format:
  GITGUARDIAN_API_KEY=<Replace-this-with-gitguardian-key>. Make sure to add the .container_env file
  to your .gitignore to keep the API key secure.

- Update the _pre-commit_ file located under .husky/pre-commit in your project. Add the following
  line of code at the end of the file to enable Gitguardian scanning before each commit:

```bash
ggshield secret scan pre-commit
```

- Finally, add the `.container_env` file as an environment file to the `docker-compose.build.yml`
  file, specifically under the `local-dev` attribute. This ensures that the environment variables
  defined in `.container_env` are available to the local-dev service. Here's an example:

```yml
services:
    local-dev:
        env_file:
            - ../.container_env
        image:.......
        volumes:
            - .....
```

## Testing

### Unit Tests

- Run all unit tests `npm run jest`
- Run all unit tests with test coverage report `npm run jest:coverage`

### End-to-end API Tests

- Start the API with `npm run start:api`
- Open a new terminal and run `npx nx test api-e2e`

## Troubleshooting

If you can't get the remote containers working here are some things to try:

- If there is a "Docker Compose is required" error when trying to start the remote container in VS
  Code then:
  - Check that "docker compose version" runs as expected in a WSL terminal. If it does not then
    docker compose is not installed properly.
  - Open the user settings in VS Code and search for "Compose". This should bring you to a setting
    to configure the Docker compose command. If it says "docker-compose" try changing it to "docker
    compose" and reopening the IDE.
- If there is a "docker daemon not started" error try running "sudo dockerd". If this is successful
  the output will have something similar to "API listen on /var/run/docker.sock" near the bottom.
  From here open a new WSL terminal and try the command again.
  - If there is still an issue and you haven't yet added a user to the docker group, please complete
    those steps and try again.
- A reinstall of VS Code server within Ubuntu can be forced by running 'rm -rf ~/.vscode-server'.
  Next time you run "code" the VS Code server components will reinstall.
- Terminating and restarting the WSL distro using "wsl -t" and "wsl -d"

### Network issues

Things to try if you're encountering network issues:

- Ensure you have the correct anti-virus policy applied:
  - Find McAfee/Trellix icon in system tray
  - Right click, Manage features -> DLP Endpoint Console
  - Click "About" in nav menu
  - Check "Name" under "Policy"
  - Ensure policy name is "<Domain> Endpoint Policy-dev"
- Update /etc/resolv.conf
  - add following to file:
  ```
  nameserver 10.181.14.2
  nameserver 10.227.52.40
  nameserver 89.101.160.5
  nameserver 89.101.160.4
  nameserver 10.181.14.1
  nameserver 10.227.127.1
  nameserver 10.228.127.1
  nameserver 8.8.8.8
  ```

## Tips

- You can open a WSL terminal as root using the option "-u root"
