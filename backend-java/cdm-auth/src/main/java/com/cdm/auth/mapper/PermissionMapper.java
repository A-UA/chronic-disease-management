package com.cdm.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cdm.auth.entity.PermissionEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Collection;
import java.util.List;

@Mapper
public interface PermissionMapper extends BaseMapper<PermissionEntity> {

    /**
     * 通过角色 ID 集合批量查询关联的权限 code
     */
    List<String> selectPermCodesByRoleIds(@Param("roleIds") Collection<Long> roleIds);
}
