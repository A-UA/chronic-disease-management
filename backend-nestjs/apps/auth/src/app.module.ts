import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { databaseConfig } from '@cdm/shared';
import { AuthController } from './auth/auth.controller.js';
import { AuthService } from './auth/auth.service.js';
import { JwtProvider } from './auth/jwt.provider.js';
import { MenuService } from './menu/menu.service.js';
import { UserEntity } from './user/user.entity.js';
import { TenantEntity } from './organization/tenant.entity.js';
import { OrganizationEntity } from './organization/organization.entity.js';
import { OrganizationUserEntity } from './organization/organization-user.entity.js';
import { OrganizationUserRoleEntity } from './organization/organization-user-role.entity.js';
import { RoleEntity } from './rbac/role.entity.js';
import { PermissionEntity } from './rbac/permission.entity.js';
import { MenuEntity } from './menu/menu.entity.js';

const entities = [
  UserEntity,
  TenantEntity,
  OrganizationEntity,
  OrganizationUserEntity,
  OrganizationUserRoleEntity,
  RoleEntity,
  PermissionEntity,
  MenuEntity,
];

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [databaseConfig] }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get<string>('database.host'),
        port: config.get<number>('database.port'),
        username: config.get<string>('database.username'),
        password: config.get<string>('database.password'),
        database: config.get<string>('database.database'),
        entities,
        synchronize: false,
      }),
    }),
    TypeOrmModule.forFeature(entities),
    JwtModule.register({
      secret: process.env.JWT_SECRET || 'your-jwt-secret-here-must-match-python',
      signOptions: { expiresIn: '7d' },
    }),
  ],
  controllers: [AuthController],
  providers: [AuthService, JwtProvider, MenuService],
})
export class AppModule {}
