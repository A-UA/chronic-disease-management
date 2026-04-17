import { IsEmail, IsNotEmpty, IsString } from 'class-validator';

export class LoginDto {
  @IsEmail()
  username: string;

  @IsNotEmpty()
  @IsString()
  password: string;
}

export class RegisterDto {
  @IsEmail()
  email: string;

  @IsNotEmpty()
  @IsString()
  password: string;

  @IsString()
  name?: string;
}

export class SelectOrgDto {
  orgId: string;
  selectionToken: string;
}

export class SwitchOrgDto {
  orgId: string;
}
