import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { InfraService } from './infra.service.js';

@Module({
  imports: [HttpModule],
  providers: [InfraService],
  exports: [InfraService],
})
export class InfraModule {}
