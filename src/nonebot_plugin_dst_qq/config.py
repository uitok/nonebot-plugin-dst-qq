from pydantic import BaseModel, Field
import httpx
import os


class Config(BaseModel):
    """Plugin Config Here"""
    
    # DMP API配置
    dmp_base_url: str = Field(
        default_factory=lambda: os.getenv("DMP_BASE_URL", "")
    )
    dmp_token: str = Field(
        default_factory=lambda: os.getenv("DMP_TOKEN", "")
    )
    default_cluster: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_CLUSTER", "")
    )
    
    def model_post_init(self, __context) -> None:
        """模型初始化后验证配置"""
        self._validate_config()
    
    def _validate_config(self):
        """验证必需的配置项"""
        if not self.dmp_base_url:
            raise ValueError("环境变量 DMP_BASE_URL 是必需的，请在 .env 文件中设置")
        if not self.dmp_token:
            raise ValueError("环境变量 DMP_TOKEN 是必需的，请在 .env 文件中设置")
        if not self.default_cluster:
            raise ValueError("环境变量 DEFAULT_CLUSTER 是必需的，请在 .env 文件中设置")
    
    async def get_first_cluster(self) -> str:
        """获取第一个可用的集群名称"""
        try:
            headers = {
                "Authorization": self.dmp_token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.dmp_base_url}/setting/clusters", headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    clusters = data.get("data", [])
                    if clusters:
                        # 返回第一个集群的名称
                        return clusters[0].get("clusterName", self.default_cluster)
                
                return self.default_cluster
        except Exception:
            # 如果获取失败，返回默认集群
            return self.default_cluster


# 配置实例将通过 get_plugin_config(Config) 获取
