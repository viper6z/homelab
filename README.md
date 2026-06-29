# homelab

A small AWS deployment platform lab.

The goal is to build and understand a simple path from a Git repository to containerised workloads running on an EC2 VM.

```text
Git repository
→ GitHub Actions
→ Terraform
→ AWS EC2
→ Docker Compose
→ Nginx
→ workload
```

This is a learning project, but it is also becoming a small platform shape that I could reuse later for deploying my own containerised services to AWS.

The point is not to hide everything behind a managed product or collect tools for the sake of it. I want to own the infrastructure, understand each layer, and see what actually happens when something breaks.

## What this project is

The platform layer is responsible for:

```text
Terraform
→ AWS infrastructure and state

cloud-init
→ first-boot host setup

Docker Compose
→ workload definitions and container lifecycle

Nginx
→ HTTP entry point and reverse proxy

GitHub Actions
→ validation and infrastructure deployment
```

The Python services in this repository are example workloads.

They exist to exercise the platform and to learn how different kinds of applications behave when containerised and networked together.

They are not meant to be the product itself.

## Current architecture

```text
GitHub

pull request
→ CI validates Terraform and Compose

merged pull request
→ GitHub Actions assumes an AWS role through OIDC
→ Terraform plan
→ Terraform apply


AWS

Terraform
→ VPC
→ public subnet
→ internet gateway
→ route table
→ security group
→ EC2 Ubuntu VM


EC2 Ubuntu VM

cloud-init bootstrap model
→ installs Docker Engine
→ installs Docker Compose plugin
→ installs Git
→ prepares the host for workloads

Docker Compose
├── nginx
├── homelab-api
├── tcp-service
├── udp-service
└── toolbox
```

The intended deployment model is:

```text
Terraform
→ creates or reconciles AWS infrastructure

cloud-init
→ configures a newly created VM on first boot

Docker Compose
→ starts and reconciles workloads

GitHub Actions
→ eventually updates workloads on the existing VM
```

The workload deployment part is not finished yet. Terraform CD exists, but the next step is using AWS Systems Manager to reach the running VM and trigger the Compose deployment remotely.

## Container networking

The Compose stack has two Docker networks:

```text
edge
└── nginx

backend
├── nginx
├── homelab-api
├── tcp-service
├── udp-service
└── toolbox
```

Nginx is the only service connected to both networks.

The HTTP request path is:

```text
EC2 host:80
→ nginx container:80
→ backend Docker network
→ homelab-api:5000
```

The API does not expose a host port directly. Nginx reaches it through Docker Compose service discovery:

```text
http://homelab-api:5000
```

This means the configuration uses service names instead of hardcoded container IP addresses.

## Example workloads

| Component     | What it does                                                           |
| ------------- | ---------------------------------------------------------------------- |
| `homelab-api` | Small Flask API with welcome, uptime, and health endpoints             |
| `nginx`       | HTTP entry point and reverse proxy to the API                          |
| `tcp-service` | Small custom TCP protocol experiment                                   |
| `udp-service` | Small UDP live-text synchronisation experiment                         |
| `toolbox`     | Internal interactive client container for testing TCP and UDP services |

### HTTP API

`homelab-api` is a small Flask service.

It listens on `0.0.0.0:5000` inside its container so other containers on the backend network can reach it.

Endpoints:

```text
GET /
→ welcome response

GET /time
→ uptime response

GET /health
→ health response
```

### TCP service

The TCP service is a small application-layer protocol built with Python's standard `socket` module.

```text
Transport: TCP
Port: 9000
Encoding: UTF-8
Framing: one command per line
```

Current commands:

```text
PING
→ PONG

ECHO hello
→ ECHO hello
```

The service is only available inside the backend Docker network.

### UDP live-text service

The UDP service is a small real-time text relay.

```text
client joins
→ JOIN

client changes text
→ UPDATE <text>

server broadcasts latest state
→ TEXT <sequence> <text>
```

The server increments a sequence number for each update. Clients ignore older updates if UDP datagrams arrive out of order.

This is intentionally not a collaborative editor. The newest update wins, and later full-state updates make missed packets acceptable for this experiment.

## AWS infrastructure

Terraform currently manages:

```text
VPC: 10.0.0.0/16
→ public subnet: 10.0.1.0/24
→ internet gateway
→ route table
→ security group
→ EC2 key pair
→ Ubuntu EC2 instance
```

The project runs in AWS Stockholm:

```text
Region: eu-north-1
```

Terraform state is stored remotely in S3 so local Terraform and GitHub Actions can use the same state.

## CI and CD

### CI

CI runs on pull requests targeting `main`.

Current checks:

```text
Terraform formatting
→ Terraform validation
→ Docker Compose configuration validation
```

The aim is to catch broken infrastructure or Compose configuration before merging.

### CD

CD runs when a pull request is merged into `main`.

GitHub Actions uses OpenID Connect to get temporary AWS credentials instead of storing long-lived AWS access keys in GitHub.

The current CD flow is:

```text
merged pull request
→ GitHub Actions OIDC login
→ Terraform init
→ Terraform plan
→ Terraform apply
```

At the moment, this handles infrastructure convergence.

The next CD milestone is:

```text
GitHub Actions
→ AWS Systems Manager
→ existing EC2 VM
→ update workload revision
→ docker compose up -d --build
```

## Running the stack locally

From the repository root:

```bash
docker compose up --build
```

`up` creates and starts the Compose services.

`--build` tells Docker Compose to build local images before starting the stack.

Check running services:

```bash
docker compose ps
```

Test the Nginx to API path:

```bash
curl -i http://localhost/
curl -i http://localhost/health
```

Stop the stack:

```bash
docker compose down
```

## Testing the protocol services

The `toolbox` container is connected to the internal backend network.

Start the TCP client:

```bash
docker compose exec -it toolbox python tcp_client.py
```

Start the UDP client:

```bash
docker compose exec -it toolbox python udp_client.py
```

Run the UDP client from two terminals to see one client update the other.

## Terraform workflow

From the `terraform` directory:

```bash
terraform init
terraform plan
terraform apply
```

```text
terraform init
→ initialises the working directory and backend

terraform plan
→ shows the infrastructure changes Terraform wants to make

terraform apply
→ performs those changes
```

## Repository layout

```text
.
├── .github/
│   └── workflows/           # CI and CD workflows
├── docs/                    # Logbook and project notes
├── homelab-api/             # Flask API example workload
├── nginx/                   # Nginx service and reverse-proxy config
├── tcp-service/             # TCP protocol server and client
├── terraform/               # AWS infrastructure and bootstrap config
│   ├── bootstrap/           # Long-lived IAM and GitHub OIDC setup
│   └── cloud-init.yaml      # First-boot host bootstrap configuration
├── toolbox/                 # Internal TCP and UDP test clients
├── udp-service/             # UDP live-text service
└── compose.yaml             # Root Compose configuration
```

## Things I have learned so far

* A container port and a host port are different things.
* `127.0.0.1` inside a container means that container itself.
* Docker Compose service names become internal DNS names on shared networks.
* TCP is a byte stream, so application protocols need their own framing.
* UDP preserves message boundaries but does not guarantee delivery or ordering.
* A VPC route to `0.0.0.0/0` and an inbound security-group rule from `0.0.0.0/0` are very different things.
* Terraform state is part of the deployment system, which is why remote state matters before multiple actors start applying infrastructure.
* OIDC lets GitHub Actions obtain temporary AWS credentials without keeping AWS keys in the repository or GitHub secrets.
* First-boot host setup and recurring workload deployment are different problems.

## What is not implemented yet

This is deliberately still a small platform.

The next layers are:

```text
AWS Systems Manager access
→ remote administration without depending on public SSH

workload CD
→ deploy Compose changes to the existing VM after merge

public HTTP access
→ open the intended ingress path safely

TLS and domain setup
→ HTTPS rather than plain HTTP

hardening
→ tighten IAM, access paths, host configuration, and failure handling

tests
→ grow application and integration testing with the workloads
```

## Notes

The build-up of the project is documented in [`docs/logbook.md`](docs/logbook.md).

The repository is evolving as I learn, but the shape is intentionally coherent:

```text
Git repository
→ GitHub Actions
→ Terraform
→ AWS infrastructure
→ EC2 host
→ Docker Compose
→ containerised workloads
```

