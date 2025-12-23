<template>
  <SettingsButton @open="settingsStore.showSettings = true" />

  <div
    v-if="settingsStore.showSettings"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
  >
    <div class="bg-white rounded-lg max-w-4xl w-full h-[90vh] flex flex-col overflow-hidden">
      <div class="flex items-center justify-between p-6 border-b flex-shrink-0">
        <div class="flex items-center space-x-4">
          <h2 class="text-xl font-semibold">设置</h2>
          <div class="flex space-x-1">
            <button
              @click="activeTab = 'providers'"
              :class="[
                'px-3 py-1 rounded text-sm font-medium transition-colors',
                activeTab === 'providers' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:text-gray-800'
              ]"
            >
              AI模型
            </button>
            <button
              @click="activeTab = 'params'"
              :class="[
                'px-3 py-1 rounded text-sm font-medium transition-colors',
                activeTab === 'params' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:text-gray-800'
              ]"
            >
              模型参数
            </button>
            <button
              @click="activeTab = 'prompts'"
              :class="[
                'px-3 py-1 rounded text-sm font-medium transition-colors',
                activeTab === 'prompts' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:text-gray-800'
              ]"
            >
              提示词规则
            </button>
            <a
              v-if="showGithubLink"
              href="https://github.com/fish2018"
              target="_blank"
              rel="noopener noreferrer"
              class="p-1 hover:bg-gray-100 rounded transition-colors"
              title="GitHub"
            >
              <svg class="w-5 h-5 text-gray-600 hover:text-gray-800" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.374 0 0 5.373 0 12 0 17.302 3.438 21.8 8.207 23.387c.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
              </svg>
            </a>
          </div>
        </div>
        <button
          @click="settingsStore.showSettings = false"
          class="p-1 hover:bg-gray-100 rounded"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <ProvidersTab
          v-if="activeTab === 'providers'"
          :providers="settingsStore.providers"
          :batch-testing-states="modelTesting.batchTestingStates.value"
          :testing-provider="modelTesting.testingProvider.value"
          @show-add-provider-type="providerMgmt.showAddProviderTypeDialog.value = true"
          @edit-provider="providerMgmt.editProvider"
          @delete-provider="providerMgmt.deleteProvider"
          @batch-test="modelTesting.batchTestModels"
          @show-add-model="modelMgmt.showAddModel"
          @edit-model="modelMgmt.editModel"
          @delete-model="modelMgmt.deleteModel"
          @test-model="modelTesting.handleModelTestClick"
          @save="settingsStore.saveSettings"
          :get-default-base-url="providerMgmt.getDefaultBaseUrl"
          :get-test-button-title="modelTesting.getTestButtonTitle"
          :get-batch-test-button-title="modelTesting.getBatchTestButtonTitle"
          :get-api-type-color="modelMgmt.getApiTypeColor"
          :get-api-type-label="modelMgmt.getApiTypeLabel"
        />

        <ModelParamsTab v-if="activeTab === 'params'" />

        <PromptsTab
          v-if="activeTab === 'prompts'"
          @reset-system="promptRules.resetSystemPromptRules"
          @reset-user="promptRules.resetUserPromptRules"
          @reset-requirement="promptRules.resetRequirementReportRules"
          @reset-thinking="promptRules.resetThinkingPointsExtractionPrompt"
          @reset-generation="promptRules.resetSystemPromptGenerationPrompt"
          @reset-advice="promptRules.resetOptimizationAdvicePrompt"
          @reset-application="promptRules.resetOptimizationApplicationPrompt"
          @reset-quality-analysis-system="promptRules.resetQualityAnalysisSystemPrompt"
          @reset-user-prompt-quality-analysis="promptRules.resetUserPromptQualityAnalysis"
          @reset-user-prompt-quick-optimization="promptRules.resetUserPromptQuickOptimization"
          @toggle-slim-rules="promptRules.handleSlimRulesToggle"
        />
      </div>

      <!-- 底部按钮 -->
      <div class="flex justify-end space-x-3 p-4 border-t bg-gray-50 flex-shrink-0">
        <button
          @click="settingsStore.showSettings = false"
          class="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
        >
          取消
        </button>
        <button
          @click="promptRules.saveAndClose"
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          保存设置
        </button>
      </div>
    </div>
  </div>

  <ProviderTypeDialog
    v-if="providerMgmt.showAddProviderTypeDialog.value"
    @select="providerMgmt.selectProviderType"
    @close="providerMgmt.showAddProviderTypeDialog.value = false"
  />

  <ProviderDialog
    v-if="providerMgmt.showAddProvider.value"
    :editing="!!providerMgmt.editingProvider.value"
    :provider-type="providerMgmt.selectedProviderType.value"
    v-model:name="providerMgmt.newProvider.value.name"
    v-model:base-url="providerMgmt.newProvider.value.baseUrl"
    v-model:api-key="providerMgmt.newProvider.value.apiKey"
    :get-default-base-url="providerMgmt.getDefaultBaseUrl"
    :get-provider-template="providerMgmt.getProviderTemplate"
    @save="providerMgmt.saveProvider"
    @close="providerMgmt.closeProviderDialog"
  />

  <ModelDialog
    v-if="modelMgmt.showAddModelDialog.value"
    :editing="!!modelMgmt.editingModel.value"
    :provider="modelMgmt.getProviderForModel(modelMgmt.addingModelToProvider.value)"
    v-model:name="modelMgmt.newModel.value.name"
    v-model:id="modelMgmt.newModel.value.id"
    v-model:api-type="modelMgmt.newModel.value.apiType"
    v-model:search-keyword="modelMgmt.modelSearchKeyword.value"
    :available-models="modelMgmt.getCurrentProviderModels.value"
    :loading="modelMgmt.loadingModels.value"
    :error="modelMgmt.modelFetchError.value"
    @fetch-models="modelMgmt.fetchAvailableModels"
    @select-model="modelMgmt.selectModel"
    @save="modelMgmt.addCustomModel"
    @close="modelMgmt.closeAddModelDialog"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { useSettingsStore } from '@/stores/settingsStore'
import { useAuthStore } from '@/stores/authStore'

import SettingsButton from './components/SettingsButton.vue'
import ProvidersTab from './components/tabs/ProvidersTab.vue'
import ModelParamsTab from './components/tabs/ModelParamsTab.vue'
import PromptsTab from './components/tabs/PromptsTab.vue'
import ProviderTypeDialog from './components/dialogs/ProviderTypeDialog.vue'
import ProviderDialog from './components/dialogs/ProviderDialog.vue'
import ModelDialog from './components/dialogs/ModelDialog.vue'

import { useProviderManagement } from './composables/useProviderManagement'
import { useModelManagement } from './composables/useModelManagement'
import { useModelTesting } from './composables/useModelTesting'
import { usePromptRules } from './composables/usePromptRules'

const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const activeTab = ref<'providers' | 'params' | 'prompts'>('providers')

const providerMgmt = useProviderManagement()
const modelMgmt = useModelManagement()
const modelTesting = useModelTesting()
const promptRules = usePromptRules()
const showGithubLink = computed(() => authStore.user?.auth_type !== 'feishu')

watch(activeTab, (newTab) => {
  if (newTab === 'prompts') {
    settingsStore.openPromptEditor('system')
  }
})
</script>
