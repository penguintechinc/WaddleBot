# K8s Deployment Guide - Scoped Database Implementation
## Dal2 Beta Cluster Deployment

**Status**: Ready for deployment
**Target Cluster**: dal2 beta (k8s.dal2.beta.penguintech.io)
**Estimated Downtime**: Zero (rolling deployment)
**Rollback Time**: <5 minutes

---

## Pre-Deployment Checklist

### Prerequisites
- [ ] K8s cluster access: `kubectl config use-context dal2-beta`
- [ ] Container registry access: Docker credentials configured
- [ ] Database backup: `pg_dump waddlebot > backup-$(date +%s).sql`
- [ ] Slack notification channel ready for deployment updates
- [ ] PagerDuty escalation policy reviewed

### Code Validation
- [ ] All 15,000+ LOC committed and reviewed
- [ ] Docker images building successfully: `docker build -t waddlebot-*`
- [ ] Helm charts linting: `helm lint k8s/helm/waddlebot/`
- [ ] K8s manifests validated: `kubectl apply --dry-run=client -f k8s/manifests/`

---

## Deployment Steps

### Phase 1: Database Preparation (5 minutes)

**Step 1.1: Backup current database**
```bash
kubectl exec -it infra-postgres-0 -- pg_dump -U waddlebot waddlebot > \
  backups/pre-scoped-database-$(date +%Y%m%d-%H%M%S).sql
```

**Step 1.2: Create 34 scoped database users**
```bash
# Apply database user creation script
kubectl apply -f k8s/manifests/database/scoped-users-secret.yaml

# Create users from init script
kubectl exec -it infra-postgres-0 -- psql -U waddlebot -d waddlebot \
  -f /config/postgres/scoped-users-init.sql
```

**Step 1.3: Apply database migrations**
```bash
# Migration 030: Create platform_integrations table
kubectl exec -it infra-postgres-0 -- psql -U waddlebot -d waddlebot << 'EOF'
BEGIN;
$(cat config/postgres/migrations/030_platform_integrations.sql)
COMMIT;
EOF

# Migration 031: RLS policies
kubectl exec -it infra-postgres-0 -- psql -U waddlebot -d waddlebot << 'EOF'
BEGIN;
$(cat config/postgres/migrations/031_rls_policies.sql)
COMMIT;
EOF

# Migration 032: Data migration
kubectl exec -it infra-postgres-0 -- psql -U waddlebot -d waddlebot << 'EOF'
BEGIN;
$(cat config/postgres/migrations/032_migrate_credentials.sql)
COMMIT;
EOF
```

**Step 1.4: Verify data migration**
```bash
kubectl exec -it infra-postgres-0 -- psql -U waddlebot -d waddlebot << 'EOF'
SELECT COUNT(*) as total_credentials,
       COUNT(CASE WHEN integration_type = 'bot' THEN 1 END) as bot_credentials,
       COUNT(CASE WHEN integration_type = 'community_oauth' THEN 1 END) as community_oauth,
       COUNT(CASE WHEN integration_type = 'user_oauth' THEN 1 END) as user_oauth
FROM platform_integrations;
EOF
```

### Phase 2: Kubernetes Secrets (5 minutes)

**Step 2.1: Create Kubernetes secrets for scoped user passwords**
```bash
# Create secret for each module's database credentials
for module in discord_action slack_action twitch_action youtube_action \
              ai_interaction alias_interaction calendar_interaction \
              inventory_interaction loyalty_interaction memories_interaction \
              quote_interaction shoutout_interaction spotify_interaction \
              youtube_music_interaction discord_trigger kick_trigger \
              slack_trigger twitch_trigger youtube_live_trigger \
              ai_researcher analytics browser_source community \
              credential_manager engagement identity labels reputation \
              security video_proxy workflow hub_admin; do
  kubectl create secret generic db-password-${module} \
    --from-literal=password="mod_${module}_dev_changeme" \
    -n waddlebot
done
```

**Step 2.2: Create configmap for module DATABASE_URLs**
```bash
kubectl apply -f k8s/manifests/configmaps/module-database-urls.yaml
```

### Phase 3: Credential Manager Service (10 minutes)

**Step 3.1: Build and push credential-manager image**
```bash
docker build -t waddlebot-credential-manager:latest \
  ./core/credential_manager_module/
docker tag waddlebot-credential-manager:latest \
  registry.penguintech.io/waddlebot/credential-manager:latest
docker push registry.penguintech.io/waddlebot/credential-manager:latest
```

**Step 3.2: Deploy credential-manager service**
```bash
kubectl apply -f k8s/manifests/core/credential-manager.yaml

# Wait for deployment
kubectl rollout status deployment/credential-manager -n waddlebot --timeout=5m
```

**Step 3.3: Verify health check**
```bash
kubectl exec -it deployment/credential-manager -n waddlebot -- \
  curl -f http://localhost:8080/health
```

### Phase 4: Rolling Module Deployment (30 minutes)

**Step 4.1: Update module environment variables**
```bash
# Update all modules with new DATABASE_URL pointing to scoped users
kubectl patch deployment action-twitch -n waddlebot \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","env":[{"name":"DATABASE_URL","valueFrom":{"configMapKeyRef":{"name":"module-db-urls","key":"action-twitch"}}}]}]}}}}'

# Repeat for all 33 other modules...
```

**Step 4.2: Rolling restart action modules (pushing)**
```bash
kubectl rolling-update deployment action-discord \
  --image=waddlebot-action-discord:latest -n waddlebot --rollback=false
# ... repeat for all action modules
```

**Step 4.3: Rolling restart trigger modules**
```bash
kubectl rolling-update deployment trigger-twitch \
  --image=waddlebot-trigger-twitch:latest -n waddlebot --rollback=false
# ... repeat for all trigger modules
```

**Step 4.4: Rolling restart core modules**
```bash
kubectl rolling-update deployment core-router \
  --image=waddlebot-core-router:latest -n waddlebot --rollback=false
# ... repeat for all core modules
```

### Phase 5: Verification (10 minutes)

**Step 5.1: Verify all modules are healthy**
```bash
# Check all deployments
kubectl get deployments -n waddlebot -o wide

# Check pod status
kubectl get pods -n waddlebot --all-namespaces | grep -v Running

# Check logs for errors
kubectl logs -l app=action-twitch -n waddlebot --tail=50
```

**Step 5.2: Run RLS policy validation**
```bash
# Connect as twitch_action user, verify can't see discord credentials
kubectl exec -it infra-postgres-0 -- psql -U twitch_action -d waddlebot << 'EOF'
SELECT COUNT(*) as twitch_credentials
FROM platform_integrations
WHERE platform = 'twitch';

SELECT COUNT(*) as discord_should_be_zero
FROM platform_integrations
WHERE platform = 'discord';
EOF
```

**Step 5.3: Verify credential refresh service is polling**
```bash
# Check credential-manager logs
kubectl logs -l app=credential-manager -n waddlebot --tail=50

# Check for "Credential refresh check" messages
```

**Step 5.4: API endpoint testing**
```bash
# Test hub admin credential management API
curl -X GET http://hub-api.dal2.beta.penguintech.io/api/admin/platform-config

# Test credential refresh
curl -X POST http://hub-api.dal2.beta.penguintech.io/api/admin/credentials/test \
  -H "Content-Type: application/json" \
  -d '{"credentialId": 1}'
```

---

## Rollback Procedure

If deployment fails or critical issues occur:

### Immediate Rollback (< 5 minutes)
```bash
# Revert all modules to previous image
kubectl rollout undo deployment/action-twitch -n waddlebot
kubectl rollout undo deployment/trigger-twitch -n waddlebot
# ... repeat for all deployments

# Restart postgres with old schema
kubectl delete pod infra-postgres-0 -n waddlebot
# Pod will respawn with backup database volume
```

### Data Rollback (if needed)
```bash
# Restore from backup
kubectl exec -it infra-postgres-0 -- psql -U waddlebot -d waddlebot << EOF
DROP TABLE IF EXISTS platform_integrations;
$(cat backups/pre-scoped-database-*.sql)
EOF
```

### Delete new resources
```bash
kubectl delete secret db-password-* -n waddlebot
kubectl delete configmap module-database-urls -n waddlebot
kubectl delete deployment credential-manager -n waddlebot
```

---

## Post-Deployment Validation

### Automated Tests

**Run RLS policy tests**:
```bash
bash tests/integration/rls_policies_test.sh
```

**Run credential refresh tests**:
```bash
bash tests/integration/credential_refresh_test.sh
```

**Run module access tests**:
```bash
bash tests/smoke/module_db_access_test.sh
```

### Manual Verification

**1. Verify platform isolation**
```bash
# As twitch_action user
psql -h dal2.beta.db.penguintech.io -U twitch_action -d waddlebot
> SELECT COUNT(*) FROM platform_integrations WHERE platform = 'twitch';
# Should return: 1+ (depending on how many twitch bots configured)

> SELECT COUNT(*) FROM platform_integrations WHERE platform = 'discord';
# Should return: 0 (RLS blocks access)
```

**2. Verify credential refresh**
```bash
# Insert test credential with near-future expiry
psql -h dal2.beta.db.penguintech.io -U waddlebot -d waddlebot << 'EOF'
INSERT INTO platform_integrations
  (platform, integration_type, access_token, refresh_token, expires_at, is_active)
VALUES
  ('twitch', 'bot', 'test_token', 'test_refresh', NOW() + INTERVAL '2 minutes', TRUE);
EOF

# Watch credential-manager logs for refresh
kubectl logs -f deployment/credential-manager -n waddlebot | grep "refresh"

# Verify token was updated
psql -h dal2.beta.db.penguintech.io -U waddlebot -d waddlebot \
  -c "SELECT expires_at FROM platform_integrations WHERE platform='twitch' AND id > (SELECT MAX(id)-1 FROM platform_integrations);"
```

**3. Verify column-level security**
```bash
# As action module user
psql -h dal2.beta.db.penguintech.io -U twitch_action -d waddlebot

> SELECT id, email, username FROM hub_users LIMIT 1;
# Should succeed - these columns are readable

> SELECT password_hash FROM hub_users LIMIT 1;
# Should FAIL - no column-level access to password_hash
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Database Connection Health**
   - 34 scoped users successfully connected
   - Connection pool size stable
   - No connection timeout errors

2. **Credential Refresh Success Rate**
   - tokens_refreshed_total metric > 0
   - refresh_failures_total < 1% of refreshes
   - Refresh latency < 100ms median

3. **RLS Policy Enforcement**
   - No cross-platform credential access attempts
   - All query plans include RLS filter pushdown
   - Query latency overhead < 10%

### Alert Thresholds

```yaml
alerts:
  - RLSBypassAttempt: IF (platform_access_denied_count > 10 / 5m)
  - CredentialRefreshFailure: IF (refresh_failures_total > 5 / hour)
  - DBConnectionFailure: IF (failed_connections > 3 / minute)
  - CrossPlatformAccess: IF (detected_unauthorized_access)
```

---

## Timeline

| Phase | Task | Duration | Start | End |
|-------|------|----------|-------|-----|
| 1 | Database prep | 5 min | T+0 | T+5 |
| 2 | K8s secrets | 5 min | T+5 | T+10 |
| 3 | Credential-manager | 10 min | T+10 | T+20 |
| 4 | Rolling deployment | 30 min | T+20 | T+50 |
| 5 | Verification | 10 min | T+50 | T+60 |
| **Total** | **All Phases** | **~60 minutes** | **T+0** | **T+60** |

---

## Support & Escalation

**On-Call Teams**:
- Database: @db-oncall
- Kubernetes: @k8s-oncall
- Platform: @platform-oncall

**Emergency Contact**:
- Slack: #waddlebot-deployment-emergency
- PagerDuty: "Scoped Database Deployment"

**Rollback Decision**:
- If any critical test fails → **ROLLBACK IMMEDIATELY**
- If >20% of modules unhealthy → **ROLLBACK IMMEDIATELY**
- If credential refresh not working → **PAUSE, FIX, RETRY**

---

## Success Criteria

✅ All 34 modules connecting with scoped users
✅ RLS policies preventing cross-platform access
✅ Credential refresh service polling every 60 seconds
✅ Zero data loss from migration
✅ Hub admin UI managing credentials
✅ All pods reporting healthy
✅ <10% performance degradation from RLS overhead

---

**Document Version**: 1.0
**Last Updated**: February 5, 2026
**Next Review**: Post-deployment (1 week)
