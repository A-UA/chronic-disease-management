import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, IsNull, Or, Equal } from 'typeorm';
import { MenuEntity } from './menu.entity.js';
import type {
  ListPayload,
  CreatePayload,
  CreateMenuData,
  UpdateMenuData,
  PaginatedResult,
  MenuVO,
  SuccessVO,
} from '@cdm/shared';

export interface MenuNode {
  id: string;
  name: string;
  code: string;
  menuType: string;
  path: string | null;
  icon: string | null;
  permissionCode: string | null;
  sort: number;
  isVisible: boolean;
  isEnabled: boolean;
  meta: Record<string, unknown> | null;
  children: MenuNode[];
}

@Injectable()
export class MenuService {
  constructor(
    @InjectRepository(MenuEntity)
    private readonly menuRepo: Repository<MenuEntity>,
  ) {}

  async list(payload: ListPayload): Promise<PaginatedResult<MenuVO>> {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [entities, total] = await this.menuRepo.findAndCount({ skip, take: limit });
    return { items: entities.map(MenuService.toVO), total };
  }

  async create(payload: CreatePayload<CreateMenuData>): Promise<MenuVO> {
    const entity = this.menuRepo.create({
      ...payload.data,
    });
    const saved = await this.menuRepo.save(entity);
    return MenuService.toVO(saved);
  }

  async update(id: string, data: UpdateMenuData): Promise<MenuVO | null> {
    await this.menuRepo.update(id, data);
    const updated = await this.menuRepo.findOneBy({ id });
    return updated ? MenuService.toVO(updated) : null;
  }

  async delete(id: string): Promise<SuccessVO> {
    await this.menuRepo.delete(id);
    return { success: true };
  }

  async getMenuTree(tenantId: string, permCodes: Set<string>): Promise<MenuNode[]> {
    const allMenus = await this.menuRepo.find({
      where: {
        isEnabled: true,
        tenantId: Or(IsNull(), Equal(tenantId)),
      },
      order: { sort: 'ASC' },
    });

    const visibleMenus = allMenus.filter(
      (m) => !m.permissionCode || permCodes.has(m.permissionCode),
    );

    return this.buildTree(visibleMenus);
  }

  static toVO(entity: MenuEntity): MenuVO {
    return {
      id: entity.id,
      parentId: entity.parentId,
      tenantId: entity.tenantId,
      name: entity.name,
      code: entity.code,
      menuType: entity.menuType,
      path: entity.path,
      icon: entity.icon,
      permissionCode: entity.permissionCode,
      sort: entity.sort,
      isVisible: entity.isVisible,
      isEnabled: entity.isEnabled,
      meta: entity.meta,
      createdAt: entity.createdAt,
      updatedAt: entity.updatedAt,
    };
  }

  private buildTree(menus: MenuEntity[]): MenuNode[] {
    const menuMap = new Map<string, MenuNode>();
    for (const m of menus) {
      menuMap.set(m.id, {
        id: m.id,
        name: m.name,
        code: m.code,
        menuType: m.menuType,
        path: m.path,
        icon: m.icon,
        permissionCode: m.permissionCode,
        sort: m.sort,
        isVisible: m.isVisible,
        isEnabled: m.isEnabled,
        meta: m.meta,
        children: [],
      });
    }

    const visibleIds = new Set(menuMap.keys());
    const roots: MenuNode[] = [];

    for (const m of menus) {
      const node = menuMap.get(m.id)!;
      if (m.parentId && visibleIds.has(m.parentId)) {
        menuMap.get(m.parentId)!.children.push(node);
      } else {
        roots.push(node);
      }
    }

    // 剪枝
    return roots.filter(
      (item) => item.menuType !== 'directory' || item.children.length > 0,
    );
  }
}
