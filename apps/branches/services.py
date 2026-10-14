from django.db import transaction

from .models import MembershipBranchAccess


@transaction.atomic
def grant_branch_access(*, membership, branch):
    access = MembershipBranchAccess(membership=membership, branch=branch)
    access.save()
    return access

