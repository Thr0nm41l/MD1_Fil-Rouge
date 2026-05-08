from fastapi import APIRouter

router = APIRouter()

# Phase 1 endpoints:
# GET    /containers
# GET    /containers/critical
# GET    /containers/stats
# GET    /containers/map
# GET    /containers/{id}
# POST   /containers
# PUT    /containers/{id}
# DELETE /containers/{id}
# GET    /containers/{id}/history
# POST   /containers/{id}/measures
# POST   /containers/import   (Phase 2)
# GET    /containers/export   (Phase 2)
