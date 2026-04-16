import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PatientEntity } from './patient.entity';
import { PatientService } from './patient.service';
import { PatientController } from './patient.controller';

@Module({
  imports: [TypeOrmModule.forFeature([PatientEntity])],
  controllers: [PatientController],
  providers: [PatientService],
})
export class PatientModule {}
