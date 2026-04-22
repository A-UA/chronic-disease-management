package com.cdm.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cdm.auth.entity.RoleEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface RoleMapper extends BaseMapper<RoleEntity> {

    /**
     * 一次 JOIN 查出用户在指定组织下的所有直接角色 code
     */
    List<String> selectRoleCodesByOrgAndUser(@Param("orgId") Long orgId, @Param("userId") Long userId);

    /**
     * 递归 CTE 展开角色继承链，返回所有（直接 + 继承）角色 ID
     */
    List<Long> selectAllRoleIdsByOrgAndUser(@Param("orgId") Long orgId, @Param("userId") Long userId);
}
