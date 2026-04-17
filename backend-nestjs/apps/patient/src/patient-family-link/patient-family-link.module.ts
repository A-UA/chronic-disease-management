import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PatientFamilyLinkEntity } from './patient-family-link.entity.js';
import { PatientFamilyLinkService } from './patient-family-link.service.js';
import { PatientFamilyLinkController } from './patient-family-link.controller.js';

@Module({
  imports: [TypeOrmModule.forFeature([PatientFamilyLinkEntity])],
  controllers: [PatientFamilyLinkController],
  providers: [PatientFamilyLinkService],
})
export class PatientFamilyLinkModule {}
