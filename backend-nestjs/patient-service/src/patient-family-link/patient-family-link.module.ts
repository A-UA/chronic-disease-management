import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PatientFamilyLinkEntity } from './patient-family-link.entity';
import { PatientFamilyLinkService } from './patient-family-link.service';
import { PatientFamilyLinkController } from './patient-family-link.controller';

@Module({
  imports: [TypeOrmModule.forFeature([PatientFamilyLinkEntity])],
  controllers: [PatientFamilyLinkController],
  providers: [PatientFamilyLinkService],
})
export class PatientFamilyLinkModule {}
