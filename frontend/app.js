const { createApp, ref, computed, onMounted } = Vue;

const API_base = 'http://localhost:5006';

// --- Sub-Components ---
const ResourceBar = {
    props: ['label', 'alloc', 'total', 'unit'],
    template: `
        <div>
            <div class="flex justify-between text-xs mb-1">
                <span class="text-gray-400">{{ label }}</span>
                <span class="text-white font-mono">{{ alloc }} / {{ total }} {{ unit }}</span>
            </div>
            <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 rounded-full transition-all duration-500"
                     :style="{ width: Math.min((alloc / total) * 100, 100) + '%' }"></div>
            </div>
        </div>
    `
};

const ResourceCard = {
    props: ['title', 'alloc', 'total', 'unit', 'icon'],
    template: `
        <div class="bg-dark-900 rounded-lg p-4 border border-gray-700">
            <h4 class="text-gray-400 text-sm mb-2 uppercase tracking-wide font-bold">{{ title }}</h4>
            <div class="flex items-end gap-2 mb-2">
                <span class="text-2xl font-bold text-white">{{ alloc }}</span>
                <span class="text-sm text-gray-500 mb-1">/ {{ total }} {{ unit }}</span>
            </div>
            <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-blue-500 to-emerald-400 rounded-full transition-all duration-500"
                     :style="{ width: Math.min((alloc / total) * 100, 100) + '%' }"></div>
            </div>
        </div>
    `
};

createApp({
    components: {
        'resource-bar': ResourceBar,
        'resource-card': ResourceCard
    },
    setup() {
        const servers = ref([]);
        const loading = ref(true);
        const lastUpdated = ref(null);

        // Navigation
        const currentView = ref('list'); // 'list' | 'detail'
        const selectedServerId = ref(null);

        // Selection Computed
        const selectedServer = computed(() => {
            return servers.value.find(s => s.id === selectedServerId.value);
        });

        // Modal State
        const showCreateModal = ref(false);
        const creating = ref(false);
        const newPod = ref({
            pod_id: '',
            image_url: '',
            namespace: '',
            route: '',
            requested: { cpus: 0.5, ram_gb: 0.5, storage_gb: 1.0 }
        });

        // Logs State
        const showLogsModal = ref(false);
        const logs = ref('');
        const logPodId = ref(null);
        const logInterval = ref(null);
        const logContainer = ref(null);

        // Security Scan State
        const showSecurityModal = ref(false);
        const scanning = ref(false);
        const scanResult = ref(null);
        const scanLogs = ref([]);
        const scanInterval = ref(null);

        // --- Methods ---

        const fetchData = async () => {
            try {
                const res = await fetch(`${API_base}/servers`);
                if (res.ok) {
                    const data = await res.json();

                    // Merge logic to preserve local state (like editing inputs) if needed
                    // For now, simple replace is okay, but let's be careful about text inputs in table
                    // We'll update the array but try to preserve UI state if possible

                    // Allow editing fields to persist if we are matching pods
                    if (selectedServer.value) {
                        // Find current server in new data
                        const newSrv = data.find(s => s.id === selectedServerId.value);
                        if (newSrv) {
                            newSrv.pods.forEach(p => {
                                // Check if we have an existing pod state
                                const oldPod = selectedServer.value.pods.find(op => op.pod_id === p.pod_id);
                                if (oldPod && oldPod._editingImage) {
                                    p._editingImage = oldPod._editingImage; // Preserve typed input
                                }
                            });
                        }
                    }

                    servers.value = data;
                    lastUpdated.value = new Date();
                }
            } catch (e) {
                console.error("Fetch error", e);
            } finally {
                loading.value = false;
            }
        };

        const selectServer = (server) => {
            selectedServerId.value = server.id;
            currentView.value = 'detail';
        };

        const goHome = () => {
            selectedServerId.value = null;
            currentView.value = 'list';
        };

        const openCreateModal = () => {
            newPod.value = {
                pod_id: '',
                image_url: 'nginx:latest',
                namespace: '',
                requested: { cpus: 0.5, ram_gb: 0.5, storage_gb: 1.0 }
            };
            showCreateModal.value = true;
        };

        const submitCreatePod = async () => {
            creating.value = true;
            try {
                const payload = {
                    server_id: selectedServerId.value,
                    pod_id: newPod.value.pod_id,
                    image_url: newPod.value.image_url,
                    namespace: newPod.value.namespace || null,
                    route: newPod.value.route || null,
                    requested: newPod.value.requested
                };

                const res = await fetch(`${API_base}/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    showCreateModal.value = false;
                    fetchData(); // Immediate refresh
                    // Note: Polling will catch the 'provisioning' state shortly
                } else {
                    alert('Creation failed: ' + await res.text());
                }
            } catch (e) {
                alert('Connection error');
            } finally {
                creating.value = false;
            }
        };

        const updatePod = async (pod) => {
            if (!pod._editingImage || pod._editingImage === pod.image_url) return;

            if (!confirm(`Update pod ${pod.pod_id} to image ${pod._editingImage}?`)) return;

            try {
                const payload = {
                    server_id: selectedServerId.value,
                    pod_id: pod.pod_id,
                    image_url: pod._editingImage
                };

                // Optimistic UI update? No, let's wait for loading
                // Actually Backend waits for blue-green, so this might take 10-20s
                // We should show a loading state on the button

                const res = await fetch(`${API_base}/update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    fetchData();
                    pod._editingImage = null; // Clear edit mode
                } else {
                    alert('Update failed: ' + await res.text());
                }
            } catch (e) {
                alert('Update error: ' + e.message);
            }
        };

        const deletePod = async (pod) => {
            if (!confirm(`Are you sure you want to delete pod ${pod.pod_id}?`)) return;

            try {
                const payload = {
                    server_id: selectedServerId.value,
                    pod_id: pod.pod_id
                };

                const res = await fetch(`${API_base}/delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    fetchData();
                } else {
                    alert('Delete failed');
                }
            } catch (e) {
                alert('Error deleting');
            }
        };

        const fetchLogs = async () => {
            if (!logPodId.value || !selectedServerId.value) return;
            try {
                const res = await fetch(`${API_base}/logs?server_id=${selectedServerId.value}&pod_id=${logPodId.value}`);
                if (res.ok) {
                    logs.value = await res.text();
                    // Auto-scroll to bottom
                    Vue.nextTick(() => {
                        if (logContainer.value) {
                            logContainer.value.scrollTop = logContainer.value.scrollHeight;
                        }
                    });
                }
            } catch (e) {
                console.error("error fetching logs", e);
            }
        };

        const showLogs = (pod) => {
            logPodId.value = pod.pod_id;
            logs.value = 'Connecting to container stream...';
            showLogsModal.value = true;
            fetchLogs();
            logInterval.value = setInterval(fetchLogs, 3000);
        };

        const closeLogs = () => {
            showLogsModal.value = false;
            if (logInterval.value) {
                clearInterval(logInterval.value);
                logInterval.value = null;
            }
            logPodId.value = null;
            logs.value = '';
        };

        const scanPod = async (pod) => {
            scanResult.value = { image: pod.image_url };
            scanLogs.value = [];
            showSecurityModal.value = true;
            scanning.value = true;

            try {
                // 1. Kick off scan
                const res = await fetch(`${API_base}/scan?server_id=${selectedServerId.value}&pod_id=${pod.pod_id}`);
                if (!res.ok) throw new Error(await res.text());

                const { scan_id } = await res.json();

                // 2. Poll for status
                scanInterval.value = setInterval(async () => {
                    try {
                        const statusRes = await fetch(`${API_base}/scan/status?scan_id=${scan_id}`);
                        if (statusRes.ok) {
                            const data = await statusRes.json();
                            scanLogs.value = data.logs;

                            if (data.status === 'success' || data.status === 'error') {
                                clearInterval(scanInterval.value);
                                scanInterval.value = null;
                                scanning.value = false;
                                scanResult.value = data.result || { error: 'Unknown error' };
                            }
                        }
                    } catch (e) {
                        console.error("Polling error", e);
                    }
                }, 2000);

            } catch (e) {
                alert('Scan initiation failed: ' + e.message);
                showSecurityModal.value = false;
                scanning.value = false;
            }
        };

        // --- Lifecycle ---
        onMounted(() => {
            fetchData();
            // Poll every 3 seconds for live updates
            setInterval(fetchData, 9000);
        });

        // Expose to template
        return {
            servers,
            loading,
            lastUpdated,
            currentView,
            selectedServer,
            selectServer,
            goHome,

            // Modal
            showCreateModal,
            openCreateModal,
            newPod,
            submitCreatePod,
            creating,

            // Actions
            updatePod,
            deletePod,

            // Logs
            showLogsModal,
            logs,
            logPodId,
            showLogs,
            closeLogs,
            logContainer,

            // Security
            showSecurityModal,
            scanning,
            scanResult,
            scanLogs,
            scanPod
        };
    }
}).mount('#app');
