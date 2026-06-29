# Deploying Saltspire MUD to AWS

This is a manual guide, not an automated script — there's no infrastructure-as-code here, just the commands and console steps to do it yourself. Before picking an option, understand the one constraint that shapes everything below:

**This app must run as exactly one process, on exactly one instance/container, at all times.** `GameEngine` keeps every piece of live state — connected players, mob HP and positions, dropped ground items, opened containers — in plain Python memory inside a single process. There's no shared database or cache behind it. If you ever run two copies at once (two EC2 instances, two ECS tasks, multiple uvicorn workers), players will be randomly split between two completely separate, inconsistent worlds. So: no autoscaling, no `--workers > 1`, no rolling deployments with two tasks briefly running side by side at full traffic.

Character saves under `players/*.json` *do* persist to disk and survive restarts of that one process — but only if that disk survives too. That's the main thing each option below differs on.

## Option A — EC2 with Docker (recommended for this prototype)

Simplest option, and the EC2 instance's own disk persists across reboots, so `players/` survives without any extra setup.

1. **Launch an instance.** EC2 console → Launch Instance → Ubuntu 22.04 LTS, `t3.micro` or `t3.small` is plenty for a prototype. Create or reuse a key pair for SSH.
2. **Security group.** Allow inbound SSH (22) from your IP, and TCP 8000 from anywhere (0.0.0.0/0) if you're connecting directly — or just 80/443 if you're putting Nginx in front (see HTTPS note below).
3. **Install Docker on the instance:**
   ```bash
   ssh -i your-key.pem ubuntu@<instance-public-ip>
   sudo apt-get update && sudo apt-get install -y docker.io
   sudo systemctl enable --now docker
   sudo usermod -aG docker ubuntu   # log out/in once for this to take effect
   ```
4. **Get the code onto the instance.** Easiest is `scp` the whole `saltspire-mud/` folder:
   ```bash
   scp -i your-key.pem -r saltspire-mud ubuntu@<instance-public-ip>:~/
   ```
5. **Build and run:**
   ```bash
   ssh -i your-key.pem ubuntu@<instance-public-ip>
   cd saltspire-mud
   docker build -t saltspire-mud .
   docker run -d --name saltspire --restart unless-stopped \
     -p 8000:8000 -v "$(pwd)/players:/app/players" saltspire-mud
   ```
6. **Play:** `http://<instance-public-ip>:8000/`. `--restart unless-stopped` brings the container back up automatically after an instance reboot.
7. **Updating code later:** `scp` the changed files over, then `docker build` + `docker stop saltspire && docker rm saltspire` + re-run the `docker run` command. Because of the single-process constraint, there will be a brief outage during the swap — that's expected for this app.

### Optional: HTTPS / a real domain

Browsers will happily talk plain `ws://` to an IP address, but if you point a domain at this and want `wss://`, put Nginx in front as a reverse proxy and get a cert with Certbot:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```
Then `sudo apt-get install -y nginx certbot python3-certbot-nginx` and `sudo certbot --nginx -d your-domain.com`. `app.js` already auto-detects `wss:` vs `ws:` based on the page's protocol, so no frontend changes are needed.

## Option B — ECS Fargate

More "cloud-native" (no OS patching, managed restarts), but loses the EC2 root disk, so persistence needs extra wiring:

1. Push the image to **ECR**: `aws ecr create-repository --repository-name saltspire-mud`, then `docker build`, `docker tag`, and `docker push` per the push commands ECR shows you.
2. Create an **EFS** filesystem and mount it into the task definition at `/app/players` (EFS is the only way to get a writable, persistent filesystem in Fargate — without it, every redeploy wipes all character saves).
3. Create an ECS **service** with **desired count = 1** (never more — see the constraint above) on a Fargate task using that image and EFS mount.
4. Put an **Application Load Balancer** in front. ALBs support WebSocket passthrough natively, so `wss://` works once you attach an ACM certificate to the HTTPS listener. Target group should health-check `/` over HTTP.
5. Because desired count must stay at 1, skip ECS's rolling-deployment-with-extra-task behavior if possible (or accept a few seconds where the old task is mid-drain and the new one isn't ready — there's no way around a brief blip given the in-memory state).

## Option C — App Runner

The least setup (point it at an ECR image or a GitHub repo and it handles the rest), but App Runner gives containers **no persistent local disk and no EFS support** — every deploy or scaling event starts from a clean filesystem, so `players/*.json` would be lost on every redeploy. Only reasonable for this app if you're fine treating it as fully ephemeral (e.g., a short-lived demo where losing characters on redeploy doesn't matter). For anything you want people's characters to survive, use Option A or B instead.

## Future-proofing note

If you outgrow the single-process constraint, the real fix is to move shared state (players, mobs, ground items) out of process memory into something external — Redis or a small database — so multiple instances can read/write the same world. That's a real architecture change, not a deployment tweak, and is out of scope for this prototype.
