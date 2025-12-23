<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" @click.stop>
      <!-- 头部 -->
      <div class="flex items-center justify-between p-6 border-b">
        <h2 class="text-xl font-semibold text-gray-900">保存提示词</h2>
        <button @click="handleCancel" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 内容 -->
      <div class="p-6 space-y-4">
        <!-- 标题 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            标题 <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.title"
            type="text"
            placeholder="请输入提示词标题"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            maxlength="200"
          />
          <p class="mt-1 text-xs text-gray-500">{{ formData.title.length }}/200</p>
        </div>

        <!-- 描述 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            描述
          </label>
          <textarea
            v-model="formData.description"
            placeholder="简短描述这个提示词的用途（可选）"
            rows="3"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            maxlength="500"
          ></textarea>
          <p class="mt-1 text-xs text-gray-500">{{ formData.description.length }}/500</p>
        </div>

        <!-- 提示词类型 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            提示词类型 <span class="text-red-500">*</span>
          </label>
          <div class="flex gap-4">
            <label class="flex items-center cursor-pointer">
              <input
                v-model="formData.promptType"
                type="radio"
                value="system"
                class="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">系统提示词</span>
            </label>
            <label class="flex items-center cursor-pointer">
              <input
                v-model="formData.promptType"
                type="radio"
                value="user"
                class="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">用户提示词</span>
            </label>
          </div>
          <p class="mt-1 text-xs text-gray-500">
            系统提示词：用于定义AI的角色和行为规则；用户提示词：用于具体任务和指令
          </p>
        </div>

        <!-- 用户提示词扩展字段 -->
        <template v-if="formData.promptType === 'user'">
          <!-- 系统提示词 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              系统提示词（可选）
            </label>
            <textarea
              v-model="formData.systemPrompt"
              placeholder="输入AI助手的系统提示词（可选）"
              rows="4"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none font-mono text-sm"
              maxlength="5000"
            ></textarea>
            <p class="mt-1 text-xs text-gray-500">{{ formData.systemPrompt.length }}/5000 字符</p>
          </div>

          <!-- 对话上下文 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              对话上下文
              <span class="text-xs text-gray-500 ml-2">(JSON格式，可复用上下文)</span>
            </label>
            <textarea
              v-model="formData.conversationHistory"
              placeholder='请输入对话历史，示例：[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]'
              rows="6"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none font-mono text-xs"
              :class="{ 'border-red-500': conversationFormatError }"
            ></textarea>
            <p v-if="conversationFormatError" class="mt-1 text-xs text-red-600">
              ⚠️ JSON格式错误：{{ conversationFormatError }}
            </p>
            <p v-else class="mt-1 text-xs text-gray-500">
              {{ formData.conversationHistory.length }}/10000 字符
              <button 
                v-if="formData.conversationHistory"
                @click="formatConversationJson"
                class="ml-2 text-blue-600 hover:text-blue-700 underline"
              >
                格式化
              </button>
              <button 
                @click="showConversationHelp = !showConversationHelp"
                class="ml-2 text-blue-600 hover:text-blue-700 underline"
              >
                {{ showConversationHelp ? '隐藏' : '查看' }}示例
              </button>
            </p>
            <div v-if="showConversationHelp" class="mt-2 p-3 bg-blue-50 border border-blue-200 rounded text-xs">
              <p class="font-semibold mb-1">标准格式示例：</p>
              <pre class="bg-white p-2 rounded overflow-x-auto whitespace-pre-wrap">{{ conversationExample }}</pre>
            </div>
          </div>
        </template>

        <!-- 标签 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            标签
          </label>
          <div class="flex flex-wrap gap-2 mb-2">
            <span
              v-for="tag in formData.tags"
              :key="tag"
              class="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
            >
              {{ tag }}
              <button @click="removeTag(tag)" class="ml-2 text-blue-500 hover:text-blue-700">×</button>
            </span>
          </div>
          <div class="flex gap-2">
            <input
              v-model="newTag"
              type="text"
              placeholder="输入标签后按回车添加"
              @keyup.enter="addTag"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              @click="addTag"
              class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              添加
            </button>
          </div>
        </div>

        <!-- 是否公开 -->
        <div class="flex items-center">
          <input
            v-model="formData.isPublic"
            type="checkbox"
            id="isPublic"
            class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label for="isPublic" class="ml-2 text-sm text-gray-700">
            公开分享（其他用户可以看到）
          </label>
        </div>

        <!-- 提示词内容 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            提示词内容 <span class="text-red-500">*</span>
          </label>
          <!-- 如果有内容就显示预览，没有就显示编辑框 -->
          <div v-if="promptContent && promptContent.trim()" class="p-3 bg-gray-50 border border-gray-200 rounded-lg max-h-40 overflow-y-auto text-sm text-gray-600">
            {{ promptContent.slice(0, 200) }}{{ promptContent.length > 200 ? '...' : '' }}
          </div>
          <textarea
            v-else
            v-model="formData.content"
            placeholder="请输入或粘贴提示词内容..."
            rows="8"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
          ></textarea>
          <p class="mt-1 text-xs text-gray-500">共 {{ (promptContent || formData.content).length }} 个字符</p>
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="flex justify-end gap-3 p-6 border-t bg-gray-50">
        <button
          @click="handleCancel"
          class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          取消
        </button>
        <button
          @click="handleSave"
          :disabled="!formData.title.trim() || isSaving"
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
        >
          <span v-if="isSaving" class="flex items-center">
            <svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            保存中...
          </span>
          <span v-else>保存</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  isOpen: boolean
  promptContent: string
  isSaving: boolean
  initialTitle?: string  // 用于编辑已有提示词时传入初始标题
}>()

const emit = defineEmits<{
  save: [data: {
    title: string
    description: string
    tags: string[]
    isPublic: boolean
    promptType: string
    content?: string
    systemPrompt?: string
    conversationHistory?: string
  }]
  cancel: []
}>()

const formData = ref({
  title: '',
  description: '',
  tags: [] as string[],
  isPublic: false,
  promptType: 'system',
  content: '',
  systemPrompt: '',
  conversationHistory: ''
})

const newTag = ref('')
const conversationFormatError = ref('')
const showConversationHelp = ref(false)
const conversationExample = `[
  {
    "role": "user",
    "content": "我牙疼"
  },
  {
    "role": "assistant",
    "content": "牙疼多久了？有什么特别的症状吗？"
  }
]`

/**
 * 从提示词内容中提取标题
 * 支持 Markdown 和 XML 格式
 */
const extractTitleFromContent = (content: string): string => {
  if (!content.trim()) {
    return `提示词_${new Date().toLocaleDateString()}`
  }

  let autoTitle = ''
  
  // 检测是否是 XML 格式
  if (content.trim().startsWith('<')) {
    // XML 格式：优先级顺序提取标题
    
    // 1. 尝试提取 <title> 标签内容
    const titleMatch = content.match(/<title[^>]*>(.*?)<\/title>/i)
    if (titleMatch && titleMatch[1]) {
      autoTitle = titleMatch[1].trim()
      // 移除可能的 "Role:" 前缀
      autoTitle = autoTitle.replace(/^Role:\s*/i, '').trim()
    }
    
    // 2. 如果没有 <title> 标签，尝试提取表示 Role 的属性和内容
    // 支持多种属性名：title, name, id, type 等
    if (!autoTitle) {
      // 匹配任何属性名为 "Role"（不区分大小写）的标签
      const rolePatterns = [
        /<\w+\s+title=["']role["'][^>]*>([^<]+)/i,     // title="Role"
        /<\w+\s+name=["']role["'][^>]*>([^<]+)/i,      // name="Role"
        /<\w+\s+id=["']role["'][^>]*>([^<]+)/i,        // id="Role"
        /<\w+\s+type=["']role["'][^>]*>([^<]+)/i,      // type="Role"
        /<section[^>]*>[\s\n]*role:?\s*([^<]+)/i,      // <section>Role: xxx
        /<role[^>]*>([^<]+)/i                          // <role>xxx</role>
      ]
      
      for (const pattern of rolePatterns) {
        const match = content.match(pattern)
        if (match && match[1]) {
          autoTitle = match[1].trim()
          // 移除可能的 "Role:" 或 "角色:" 前缀
          autoTitle = autoTitle.replace(/^(role|角色)[:：]\s*/i, '').trim()
          if (autoTitle) break
        }
      }
    }
    
    // 3. 如果还没找到，提取第一个有意义的文本内容
    if (!autoTitle) {
      const textMatch = content.match(/>([^<]+)</g)
      if (textMatch && textMatch[0]) {
        autoTitle = textMatch[0].replace(/>/g, '').replace(/</g, '').trim()
      }
    }
  } else {
    // Markdown 格式：提取第一行非空内容
    const lines = content.trim().split('\n')
    for (const line of lines) {
      const trimmedLine = line.trim()
      if (trimmedLine) {
        // 如果是以 '# Role:' 开头，提取 Role 后面的内容
        if (trimmedLine.startsWith('# Role:')) {
          const roleContent = trimmedLine.substring(8).trim() // 去掉 '# Role:' (8个字符)
          if (roleContent) {
            autoTitle = roleContent
            break
          }
        } else {
          // 移除 markdown 标记（#, *, - 等）
          autoTitle = trimmedLine
            .replace(/^#{1,6}\s*/, '')  // 移除标题标记
            .replace(/^\*+\s*/, '')     // 移除列表标记
            .replace(/^-+\s*/, '')      // 移除列表标记
            .replace(/^\d+\.\s*/, '')   // 移除数字列表
            .trim()
          if (autoTitle) {
            break
          }
        }
      }
    }
  }
  
  // 如果没有找到合适的标题，使用默认标题
  if (!autoTitle) {
    autoTitle = `提示词_${new Date().toLocaleDateString()}`
  }
  
  // 限制标题长度
  if (autoTitle.length > 50) {
    autoTitle = autoTitle.substring(0, 50) + '...'
  }
  
  return autoTitle
}

const validateConversationJson = (jsonStr: string): string => {
  if (!jsonStr.trim()) {
    return ''
  }

  try {
    const parsed = JSON.parse(jsonStr)
    if (!Array.isArray(parsed)) {
      return '必须是数组格式'
    }
    for (let i = 0; i < parsed.length; i++) {
      const item = parsed[i] || {}
      if (!item.role || !item.content) {
        return `第${i + 1}条消息缺少role或content字段`
      }
      if (!['user', 'assistant', 'system'].includes(item.role)) {
        return `第${i + 1}条消息的role必须是user、assistant或system`
      }
    }
    return ''
  } catch (error: any) {
    return error?.message || 'JSON格式错误'
  }
}

watch(
  () => formData.value.conversationHistory,
  (newValue) => {
    if (formData.value.promptType !== 'user') {
      conversationFormatError.value = ''
      return
    }
    conversationFormatError.value = validateConversationJson(newValue)
  }
)

watch(
  () => formData.value.promptType,
  (newType) => {
    if (newType !== 'user') {
      conversationFormatError.value = ''
    } else if (formData.value.conversationHistory) {
      conversationFormatError.value = validateConversationJson(formData.value.conversationHistory)
    }
  }
)

const formatConversationJson = () => {
  if (!formData.value.conversationHistory.trim()) return
  try {
    const parsed = JSON.parse(formData.value.conversationHistory)
    formData.value.conversationHistory = JSON.stringify(parsed, null, 2)
    conversationFormatError.value = ''
  } catch {
    conversationFormatError.value = 'JSON格式错误，无法格式化'
  }
}

// 监听对话框打开，重置表单
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    // 如果是编辑模式且有初始标题，使用原标题
    if (props.initialTitle) {
      formData.value.title = props.initialTitle
    } else {
      // 新建模式：从提示词内容自动生成标题
      formData.value.title = extractTitleFromContent(props.promptContent || '')
    }
    
    formData.value.description = ''
    formData.value.tags = []
    formData.value.isPublic = false
    formData.value.promptType = 'system'
    formData.value.content = ''
    formData.value.systemPrompt = ''
    formData.value.conversationHistory = ''
    showConversationHelp.value = false
    conversationFormatError.value = ''
  }
})

const addTag = () => {
  const tag = newTag.value.trim()
  if (tag && !formData.value.tags.includes(tag) && formData.value.tags.length < 10) {
    formData.value.tags.push(tag)
    newTag.value = ''
  }
}

const removeTag = (tag: string) => {
  formData.value.tags = formData.value.tags.filter(t => t !== tag)
}

const handleSave = () => {
  if (!formData.value.title.trim()) return
  // 如果没有promptContent，则需要content
  if (!props.promptContent && !formData.value.content.trim()) {
    alert('请输入提示词内容')
    return
  }
  if (formData.value.promptType === 'user' && conversationFormatError.value) {
    alert('请修正对话上下文JSON格式')
    return
  }
  emit('save', {
    title: formData.value.title.trim(),
    description: formData.value.description.trim(),
    tags: formData.value.tags,
    isPublic: formData.value.isPublic,
    promptType: formData.value.promptType,
    content: formData.value.content.trim(),
    systemPrompt: formData.value.promptType === 'user' ? formData.value.systemPrompt.trim() : '',
    conversationHistory: formData.value.promptType === 'user' ? formData.value.conversationHistory.trim() : ''
  })
}

const handleCancel = () => {
  emit('cancel')
}

// Backdrop click handler - unused but kept for potential future use
// const handleBackdropClick = (event: MouseEvent) => {
//   // 只有当点击的目标是背景div本身时才关闭
//   if (event.target === event.currentTarget) {
//     handleCancel()
//   }
// }
</script>
