package com.cdm.patient.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cdm.patient.entity.PatientProfileEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface PatientMapper extends BaseMapper<PatientProfileEntity> {
}
