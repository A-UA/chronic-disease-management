import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, IsNull, Or, Equal } from 'typeorm';
import { MenuEntity } from './menu.entity';

export interface MenuNode {
  id: number;
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

  async getMenuTree(tenantId: number, permCodes: Set<string>): Promise<MenuNode[]> {
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
    const menuMap = new Map<number, MenuNode>();
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
