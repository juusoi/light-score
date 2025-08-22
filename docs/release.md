# Release

## Preconditions

- Main branch green (CI + security)
- Terraform state applied
- `AWS_ROLE_TO_ASSUME` valid

## Tag

```
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

## Deploy

Automated Lightsail deploy workflow runs after security workflow success.

## Rollback

- Re-run deploy with prior image labels or
- git revert commit and push

## Verify

Check deployment ACTIVE, hit frontend URL, backend health.
