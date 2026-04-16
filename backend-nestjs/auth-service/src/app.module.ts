import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { AuthController } from './auth/auth.controller';
import { AuthService } from './auth/auth.service';
import { JwtProvider } from './auth/jwt.provider';
import { MenuService } from './menu/menu.service';
import { UserEntity } from './user/user.entity';
import { TenantEntity } from './organization/tenant.entity';
import { OrganizationEntity } from './organization/organization.entity';
import { OrganizationUserEntity } from './organization/organization-user.entity';
import { OrganizationUserRoleEntity } from './organization/organization-user-role.entity';
import { RoleEntity } from './rbac/role.entity';
import { PermissionEntity } from './rbac/permission.entity';
import { MenuEntity } from './menu/menu.entity';

const entities = [
  UserEntity, TenantEntity, OrganizationEntity,
  OrganizationUserEntity, OrganizationUserRoleEntity,
  RoleEntity, PermissionEntity, MenuEntity,
];

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432'),
      username: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASS || 'postgres',
      database: process.env.DB_NAME || 'postgres',
      entities,
      synchronize: true, // DDL 由 Alembic 管理
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
