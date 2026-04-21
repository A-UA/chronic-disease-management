package com.cdm.common.security;
import java.util.List;

public class IdentityPayload {
    private Long userId;
    private Long tenantId;
    private Long orgId;
    private List<Long> allowedOrgIds;
    private List<String> roles;

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public Long getOrgId() { return orgId; }
    public void setOrgId(Long orgId) { this.orgId = orgId; }
    public List<Long> getAllowedOrgIds() { return allowedOrgIds; }
    public void setAllowedOrgIds(List<Long> allowedOrgIds) { this.allowedOrgIds = allowedOrgIds; }
    public List<String> getRoles() { return roles; }
    public void setRoles(List<String> roles) { this.roles = roles; }
}
