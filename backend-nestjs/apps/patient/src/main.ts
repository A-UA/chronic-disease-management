import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module.js';
import { PATIENT_TCP_PORT } from '@cdm/shared';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: {
      host: '0.0.0.0',
      port: Number(process.env.PATIENT_TCP_PORT) || PATIENT_TCP_PORT,
    },
  });
  await app.listen();
  console.log(`Patient service listening on TCP port ${PATIENT_TCP_PORT}`);
}
bootstrap();
