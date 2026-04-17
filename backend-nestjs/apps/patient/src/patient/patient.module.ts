import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PatientEntity } from './patient.entity.js';
import { PatientService } from './patient.service.js';
import { PatientController } from './patient.controller.js';

@Module({
  imports: [TypeOrmModule.forFeature([PatientEntity])],
  controllers: [PatientController],
  providers: [PatientService],
})
export class PatientModule {}
