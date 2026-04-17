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
  @IsNumber()
  @IsNotEmpty()
  orgId!: number;

  @IsString()
  @IsNotEmpty()
  selectionToken!: string;
}

export class SwitchOrgBody {
  @IsNumber()
  @IsNotEmpty()
  orgId!: number;
}
