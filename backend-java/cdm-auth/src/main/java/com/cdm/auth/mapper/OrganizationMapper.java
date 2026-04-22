package com.cdm.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cdm.auth.entity.OrganizationEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface OrganizationMapper extends BaseMapper<OrganizationEntity> {

    /**
     * 递归 CTE 获取指定组织及其所有下级组织 ID
     */
    List<Long> selectDescendantIds(@Param("rootOrgId") Long rootOrgId);
}
