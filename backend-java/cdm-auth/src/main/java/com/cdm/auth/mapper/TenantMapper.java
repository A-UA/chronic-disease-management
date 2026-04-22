package com.cdm.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cdm.auth.entity.TenantEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TenantMapper extends BaseMapper<TenantEntity> {
}
