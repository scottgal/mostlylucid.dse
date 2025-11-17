# Docker Setup for Local Development

This guide explains how to set up the local development environment for mostlylucid DiSE using Docker Compose.

## Services

The `docker-compose.localdev.yml` file provides:

### 1. Grafana Loki
- **Purpose**: Log aggregation for BugCatcher
- **Port**: 3100
- **Volume**: `code_evolver_loki_data`
- **Health Check**: http://localhost:3100/ready

### 2. Qdrant
- **Purpose**: Vector database for RAG memory
- **Ports**:
  - 6333 (REST API)
  - 6334 (gRPC API)
- **Volume**: `code_evolver_qdrant_storage`
- **Dashboard**: http://localhost:6333/dashboard

### 3. Grafana
- **Purpose**: Visualization dashboard for logs
- **Port**: 3000
- **Volume**: `code_evolver_grafana_data`
- **Default Login**: admin / admin
- **Auto-configured**: Loki datasource

## Quick Start

### Start All Services

```bash
cd code_evolver
docker-compose -f docker-compose.localdev.yml up -d
```

### Check Service Status

```bash
docker-compose -f docker-compose.localdev.yml ps
```

Expected output:
```
NAME                      STATUS              PORTS
code_evolver_loki         Up (healthy)        0.0.0.0:3100->3100/tcp
code_evolver_qdrant       Up (healthy)        0.0.0.0:6333->6333/tcp, 0.0.0.0:6334->6334/tcp
code_evolver_grafana      Up (healthy)        0.0.0.0:3000->3000/tcp
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.localdev.yml logs -f

# Specific service
docker-compose -f docker-compose.localdev.yml logs -f loki
docker-compose -f docker-compose.localdev.yml logs -f qdrant
docker-compose -f docker-compose.localdev.yml logs -f grafana
```

### Stop Services

```bash
# Stop but keep data
docker-compose -f docker-compose.localdev.yml down

# Stop and remove data
docker-compose -f docker-compose.localdev.yml down -v
```

## Accessing Services

### Loki

- **URL**: http://localhost:3100
- **Push API**: http://localhost:3100/loki/api/v1/push
- **Query API**: http://localhost:3100/loki/api/v1/query

Test Loki:
```bash
curl http://localhost:3100/ready
```

### Qdrant

- **REST API**: http://localhost:6333
- **gRPC API**: localhost:6334
- **Dashboard**: http://localhost:6333/dashboard

Test Qdrant:
```bash
curl http://localhost:6333/healthz
```

List collections:
```bash
curl http://localhost:6333/collections
```

### Grafana

- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin (change on first login)

The Loki datasource is automatically provisioned.

## Configuration Files

### loki-config.yaml

Configures Loki with:
- **Storage**: Filesystem (local development)
- **Retention**: 7 days (168 hours)
- **Limits**: Appropriate for local development

### grafana-provisioning/datasources/loki.yaml

Auto-provisions Loki as the default datasource in Grafana.

## Data Persistence

All data is stored in Docker volumes:

### View Volumes

```bash
docker volume ls | grep code_evolver
```

### Inspect Volume

```bash
docker volume inspect code_evolver_loki_data
docker volume inspect code_evolver_qdrant_storage
docker volume inspect code_evolver_grafana_data
```

### Backup Volume

```bash
# Backup Loki data
docker run --rm -v code_evolver_loki_data:/data -v $(pwd):/backup alpine tar czf /backup/loki_backup.tar.gz /data

# Backup Qdrant data
docker run --rm -v code_evolver_qdrant_storage:/data -v $(pwd):/backup alpine tar czf /backup/qdrant_backup.tar.gz /data

# Backup Grafana data
docker run --rm -v code_evolver_grafana_data:/data -v $(pwd):/backup alpine tar czf /backup/grafana_backup.tar.gz /data
```

### Restore Volume

```bash
# Restore Loki data
docker run --rm -v code_evolver_loki_data:/data -v $(pwd):/backup alpine tar xzf /backup/loki_backup.tar.gz -C /
```

## Troubleshooting

### Services Won't Start

**Check Docker is running**:
```bash
docker ps
```

**Check port conflicts**:
```bash
lsof -i :3000  # Grafana
lsof -i :3100  # Loki
lsof -i :6333  # Qdrant
```

**View container logs**:
```bash
docker-compose -f docker-compose.localdev.yml logs loki
```

### Health Checks Failing

**Loki**:
```bash
docker exec code_evolver_loki wget -O- http://localhost:3100/ready
```

**Qdrant**:
```bash
docker exec code_evolver_qdrant wget -O- http://localhost:6333/healthz
```

**Grafana**:
```bash
docker exec code_evolver_grafana wget -O- http://localhost:3000/api/health
```

### Reset Everything

```bash
# Stop and remove containers, volumes, and networks
docker-compose -f docker-compose.localdev.yml down -v

# Remove orphaned volumes
docker volume prune

# Start fresh
docker-compose -f docker-compose.localdev.yml up -d
```

## Resource Usage

### Check Resource Usage

```bash
docker stats
```

### Adjust Resource Limits

Edit `docker-compose.localdev.yml` to add resource limits:

```yaml
services:
  loki:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## Production Deployment

**Note**: `docker-compose.localdev.yml` is designed for LOCAL DEVELOPMENT ONLY.

For production:
1. Use external Loki/Grafana services
2. Enable authentication
3. Use persistent storage backends (S3, etc.)
4. Configure proper retention policies
5. Set up monitoring and alerting
6. Use TLS/SSL for all connections

## Network

All services are on the same Docker network (`code_evolver_network`):

- Services can communicate using container names
- Example: Grafana connects to Loki via `http://loki:3100`

### View Network

```bash
docker network inspect code_evolver_network
```

## Updates

### Update Service Images

```bash
# Pull latest images
docker-compose -f docker-compose.localdev.yml pull

# Recreate containers with new images
docker-compose -f docker-compose.localdev.yml up -d
```

### Update Configuration

1. Edit `loki-config.yaml` or `docker-compose.localdev.yml`
2. Recreate services:

```bash
docker-compose -f docker-compose.localdev.yml up -d --force-recreate
```

## Integration with mostlylucid DiSE

### BugCatcher

BugCatcher automatically sends logs to Loki when configured:

```yaml
# config.yaml
bugcatcher:
  enabled: true
  loki:
    url: "http://localhost:3100"
    enabled: true
```

### RAG Memory

Qdrant is used for vector storage:

```yaml
# config.yaml
rag_memory:
  use_qdrant: true
  qdrant_url: "http://localhost:6333"
  collection_name: "code_evolver_rag"
```

## Tips

1. **Always use docker-compose commands** from the project root
2. **Use `-f docker-compose.localdev.yml`** to specify the file
3. **Check health status** before assuming services are ready
4. **Monitor resource usage** if experiencing performance issues
5. **Backup volumes** before major updates
6. **Use Grafana dashboards** for better log visualization

## Further Reading

- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
