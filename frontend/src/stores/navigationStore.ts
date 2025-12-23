import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './authStore'

export type ModuleType = 'generate' | 'optimize' | 'playground' | 'library' | 'community'

export interface ModuleConfig {
  id: ModuleType
  name: string
  icon: string
  path: string
  color: string
  requiresCommunity?: boolean  // 是否需要社区功能启用
}

export const useNavigationStore = defineStore('navigation', () => {
  // 状态
  const currentModule = ref<ModuleType>('generate')
  const sidebarCollapsed = ref(false)
  const isMobile = ref(false)
  const communityEnabled = ref(false)  // 社区功能是否启用

  // 所有模块配置
  const allModules: ModuleConfig[] = [
    {
      id: 'generate',
      name: '生成',
      icon: '🏠',
      path: '/generate',
      color: '#3B82F6'
    },
    {
      id: 'optimize',
      name: '优化',
      icon: '⚡',
      path: '/optimize',
      color: '#F59E0B'
    },
    {
      id: 'playground',
      name: '演练',
      icon: '🎯',
      path: '/playground',
      color: '#10B981'
    },
    {
      id: 'community',
      name: '广场',
      icon: '👥',
      path: '/community',
      color: '#EC4899',
      requiresCommunity: true  // 需要社区功能
    },
    {
      id: 'library',
      name: '我的',
      icon: '📚',
      path: '/library',
      color: '#8B5CF6'
    }
  ]

  // 根据社区功能状态过滤可见模块
  const modules = computed(() => {
    return allModules.filter(m => {
      if (m.requiresCommunity) {
        return communityEnabled.value
      }
      return true
    })
  })

  // 计算属性
  const currentModuleConfig = computed(() => {
    return modules.value.find(m => m.id === currentModule.value) || modules.value[0]
  })

  const sidebarWidth = computed(() => {
    return sidebarCollapsed.value ? '60px' : '140px'
  })

  // 方法
  const setCurrentModule = (module: ModuleType) => {
    currentModule.value = module
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  const setMobile = (mobile: boolean) => {
    isMobile.value = mobile
    // 移动端默认折叠侧边栏
    if (mobile) {
      sidebarCollapsed.value = true
    }
  }

  const getModuleByPath = (path: string): ModuleConfig | undefined => {
    return modules.value.find(m => m.path === path)
  }

  // 检查并设置社区功能状态
  const checkCommunityFeature = async () => {
    try {
      const authStore = useAuthStore()
      const config = authStore.authConfig
      
      // 只要开启了任意OAuth方式或允许注册时启用社区功能
      communityEnabled.value = !!(config?.linux_do_enabled || config?.feishu_enabled || config?.registration_enabled)
      
      console.log('社区功能状态:', {
        linux_do_enabled: config?.linux_do_enabled,
        registration_enabled: config?.registration_enabled,
        communityEnabled: communityEnabled.value
      })
    } catch (error) {
      console.error('检查社区功能失败:', error)
      communityEnabled.value = false
    }
  }

  return {
    // 状态
    currentModule,
    sidebarCollapsed,
    isMobile,
    communityEnabled,
    modules,
    
    // 计算属性
    currentModuleConfig,
    sidebarWidth,
    
    // 方法
    setCurrentModule,
    toggleSidebar,
    setMobile,
    getModuleByPath,
    checkCommunityFeature
  }
})
