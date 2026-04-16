import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ManagerAssignmentEntity } from './manager-assignment.entity';
import { ManagerAssignmentService } from './manager-assignment.service';
import { ManagerAssignmentController } from './manager-assignment.controller';

@Module({
  imports: [TypeOrmModule.forFeature([ManagerAssignmentEntity])],
  controllers: [ManagerAssignmentController],
  providers: [ManagerAssignmentService],
})
export class ManagerAssignmentModule {}
