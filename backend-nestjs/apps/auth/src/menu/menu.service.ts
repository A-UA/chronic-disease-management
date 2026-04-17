import { nextId } from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, IsNull, Or, Equal } from 'typeorm';
import { MenuEntity } from './menu.entity.js';

export interface MenuNode {
  id: string;
  name: string;
  code: string;
  menu_type: string;
  path: string | null;
  icon: string | null;
  permission_code: string | null;
  sort: number;
  is_visible: boolean;
  is_enabled: boolean;
  meta: Record<string, any> | null;
  children: MenuNode[];
}

@Injectable()
export class MenuService {
  constructor(
    @InjectRepository(MenuEntity)
    private readonly menuRepo: Repository<MenuEntity>,
  ) {}

  async list(payload: any) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.menuRepo.findAndCount({ skip, take: limit });
    return { items, total };
  }

  async create(payload: any) {
    const entity = this.menuRepo.create(payload as any);
    return this.menuRepo.save(entity);
  }

  async update(id: string, data: any) {
    await this.menuRepo.update(id, data);
    return this.menuRepo.findOne({ where: { id } as any });
  }

  async delete(id: string) {
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

  private buildTree(menus: MenuEntity[]): MenuNode[] {
    const menuMap = new Map<string, MenuNode>();
    for (const m of menus) {
      menuMap.set(m.id, {
        id: m.id,
        name: m.name,
        code: m.code,
        menu_type: m.menuType,
        path: m.path,
        icon: m.icon,
        permission_code: m.permissionCode,
        sort: m.sort,
        is_visible: m.isVisible,
        is_enabled: m.isEnabled,
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
      (item) => item.menu_type !== 'directory' || item.children.length > 0,
    );
  }
}
