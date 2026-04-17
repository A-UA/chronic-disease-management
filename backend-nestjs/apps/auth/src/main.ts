import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module.js';
import { AUTH_TCP_PORT } from '@cdm/shared';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: { host: '0.0.0.0', port: AUTH_TCP_PORT },
  });
  await app.listen();
  console.log(`Auth service listening on TCP port ${AUTH_TCP_PORT}`);
}
bootstrap();
