package com.cdm.patient.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cdm.patient.entity.HealthMetricEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface HealthMetricMapper extends BaseMapper<HealthMetricEntity> {
}
