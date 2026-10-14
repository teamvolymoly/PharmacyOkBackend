from django.contrib import admin

from .models import Branch, MembershipBranchAccess

admin.site.register(Branch)
admin.site.register(MembershipBranchAccess)

