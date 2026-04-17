import { IsString, IsNotEmpty, IsNumber } from 'class-validator';

export class LoginBody {
  @IsString()
  @IsNotEmpty()
  username!: string;

  @IsString()
  @IsNotEmpty()
  password!: string;
}

export class SelectOrgBody {
  @IsString()
  @IsNotEmpty()
  orgId!: string;

  @IsString()
  @IsNotEmpty()
  selectionToken!: string;
}

export class SwitchOrgBody {
  @IsString()
  @IsNotEmpty()
  orgId!: string;
}
