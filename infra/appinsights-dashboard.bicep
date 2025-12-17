@description('Azure region for the dashboard resource.')
param location string = resourceGroup().location

@description('Dashboard name (3-24 alphanumerics/dashes).')
param name string = 'mcp-tools-dashboard'

@description('Application Insights component name (for deep links).')
param applicationInsightsName string

@description('Dashboard default time range (ISO8601 duration, e.g. P12H, P1D).')
param timeRange string = 'P12H'

var appInsightsResourceId = '/subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroup().name}/providers/Microsoft.Insights/components/${applicationInsightsName}'

resource dashboard 'Microsoft.Portal/dashboards@2020-09-01-preview' = {
  name: name
  location: location
  properties: {
    lenses: [
      {
        order: 0
        parts: [
          // Header: Tool call analytics (Markdown)
          {
            position: { x: 0, y: 4, colSpan: 12, rowSpan: 1 }
            metadata: any({
              type: 'Extension/HubsExtension/PartType/MarkdownPart'
              inputs: []
              settings: {
                content: {
                  settings: {
                    content: '# Tool call analytics'
                    title: ''
                    subtitle: ''
                  }
                }
              }
            })
          }
          // 1) Tools/Call - Counts over time (timechart)
          {
            position: { x: 0, y: 5, colSpan: 6, rowSpan: 4 }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                }
                {
                  name: 'Scope'
                  value: {
                    resourceIds: [appInsightsResourceId]
                  }
                  isOptional: true
                }
                {
                  name: 'PartId'
                  value: guid('tile1-${name}')
                  isOptional: true
                }
                {
                  name: 'Version'
                  value: '2.0'
                  isOptional: true
                }
                {
                  name: 'TimeRange'
                  value: timeRange
                  isOptional: true
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                }
                {
                  name: 'Query'
                  value: 'dependencies\n| where tostring(customDimensions["mcp.method.name"]) == "tools/call"\n| summarize count() by bin(timestamp, 5m)\n| order by timestamp asc\n| render timechart'
                  isOptional: true
                }
                {
                  name: 'ControlType'
                  value: 'FrameControlChart'
                  isOptional: true
                }
                {
                  name: 'SpecificChart'
                  value: 'Line'
                  isOptional: true
                }
                {
                  name: 'PartTitle'
                  value: 'Tools/Call — counts over time'
                  isOptional: true
                }
                {
                  name: 'PartSubTitle'
                  value: applicationInsightsName
                  isOptional: true
                }
                {
                  name: 'Dimensions'
                  value: {
                    xAxis: {
                      name: 'timestamp'
                      type: 'datetime'
                    }
                    yAxis: [
                      {
                        name: 'count_'
                        type: 'long'
                      }
                    ]
                    aggregation: 'Sum'
                  }
                  isOptional: true
                }
                {
                  name: 'LegendOptions'
                  value: {
                    isEnabled: true
                    position: 'Bottom'
                  }
                  isOptional: true
                }
                {
                  name: 'IsQueryContainTimeRange'
                  value: false
                  isOptional: true
                }
              ]
              #disable-next-line BCP036
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              settings: {}
            }
          }
          // 2) Success vs Error over time (stacked timechart)
          {
            position: { x: 6, y: 5, colSpan: 6, rowSpan: 4 }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                }
                {
                  name: 'Scope'
                  value: {
                    resourceIds: [appInsightsResourceId]
                  }
                  isOptional: true
                }
                {
                  name: 'PartId'
                  value: guid('tile2-${name}')
                  isOptional: true
                }
                {
                  name: 'Version'
                  value: '2.0'
                  isOptional: true
                }
                {
                  name: 'TimeRange'
                  value: timeRange
                  isOptional: true
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                }
                {
                  name: 'Query'
                  value: 'dependencies\n| where tostring(customDimensions["mcp.method.name"]) == "tools/call"\n| extend tool_success_raw = tostring(customDimensions["mcp.tool.success"])\n| extend tool_success = case(tolower(tool_success_raw) == "true", "Success", tolower(tool_success_raw) == "false", "Error", tool_success_raw)\n| summarize count() by bin(timestamp, 5m), tool_success\n| order by timestamp asc\n| render timechart'
                  isOptional: true
                }
                {
                  name: 'ControlType'
                  value: 'FrameControlChart'
                  isOptional: true
                }
                {
                  name: 'SpecificChart'
                  value: 'StackedArea'
                  isOptional: true
                }
                {
                  name: 'PartTitle'
                  value: 'Tools/Call — Success vs Error'
                  isOptional: true
                }
                {
                  name: 'PartSubTitle'
                  value: applicationInsightsName
                  isOptional: true
                }
                {
                  name: 'Dimensions'
                  value: {
                    xAxis: {
                      name: 'timestamp'
                      type: 'datetime'
                    }
                    yAxis: [
                      {
                        name: 'count_'
                        type: 'long'
                      }
                    ]
                    splitBy: [
                      {
                        name: 'tool_success'
                        type: 'string'
                      }
                    ]
                    aggregation: 'Sum'
                  }
                  isOptional: true
                }
                {
                  name: 'LegendOptions'
                  value: {
                    isEnabled: true
                    position: 'Bottom'
                  }
                  isOptional: true
                }
                {
                  name: 'IsQueryContainTimeRange'
                  value: false
                  isOptional: true
                }
              ]
              #disable-next-line BCP036
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              settings: {}
            }
          }
          // 3) Success rate (%) over time (single line)
          {
            position: { x: 0, y: 9, colSpan: 6, rowSpan: 4 }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                }
                {
                  name: 'Scope'
                  value: {
                    resourceIds: [appInsightsResourceId]
                  }
                  isOptional: true
                }
                {
                  name: 'PartId'
                  value: guid('tile3-${name}')
                  isOptional: true
                }
                {
                  name: 'Version'
                  value: '2.0'
                  isOptional: true
                }
                {
                  name: 'TimeRange'
                  value: timeRange
                  isOptional: true
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                }
                {
                  name: 'Query'
                  value: 'dependencies\n| where tostring(customDimensions["mcp.method.name"]) == "tools/call"\n| extend isError = iff(tolower(tostring(customDimensions["mcp.tool.success"])) == "false", 1, 0)\n| summarize total = count(), errors = sum(isError) by bin(timestamp, 5m)\n| extend success_rate_pct = 100.0 * (total - errors) / total\n| project timestamp, success_rate_pct\n| order by timestamp asc\n| render timechart'
                  isOptional: true
                }
                {
                  name: 'ControlType'
                  value: 'FrameControlChart'
                  isOptional: true
                }
                {
                  name: 'SpecificChart'
                  value: 'Line'
                  isOptional: true
                }
                {
                  name: 'PartTitle'
                  value: 'Tools/Call — Success rate (%)'
                  isOptional: true
                }
                {
                  name: 'PartSubTitle'
                  value: applicationInsightsName
                  isOptional: true
                }
                {
                  name: 'Dimensions'
                  value: {
                    xAxis: {
                      name: 'timestamp'
                      type: 'datetime'
                    }
                    yAxis: [
                      {
                        name: 'success_rate_pct'
                        type: 'real'
                      }
                    ]
                    aggregation: 'Sum'
                  }
                  isOptional: true
                }
                {
                  name: 'LegendOptions'
                  value: {
                    isEnabled: true
                    position: 'Bottom'
                  }
                  isOptional: true
                }
                {
                  name: 'IsQueryContainTimeRange'
                  value: false
                  isOptional: true
                }
              ]
              #disable-next-line BCP036
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              settings: {}
            }
          }
          // 4) Calls by tool (bar/column chart)
          {
            position: { x: 6, y: 9, colSpan: 6, rowSpan: 4 }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                }
                {
                  name: 'Scope'
                  value: {
                    resourceIds: [appInsightsResourceId]
                  }
                  isOptional: true
                }
                {
                  name: 'PartId'
                  value: guid('tile4-${name}')
                  isOptional: true
                }
                {
                  name: 'Version'
                  value: '2.0'
                  isOptional: true
                }
                {
                  name: 'TimeRange'
                  value: timeRange
                  isOptional: true
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                }
                {
                  name: 'Query'
                  value: 'dependencies\n| where tostring(customDimensions["mcp.method.name"]) == "tools/call"\n| extend tool = coalesce(tostring(customDimensions["gen_ai.tool.name"]), target, name)\n| summarize count() by tool\n| order by count_ desc\n| render barchart'
                  isOptional: true
                }
                {
                  name: 'ControlType'
                  value: 'FrameControlChart'
                  isOptional: true
                }
                {
                  name: 'SpecificChart'
                  value: 'Bar'
                  isOptional: true
                }
                {
                  name: 'PartTitle'
                  value: 'Tools/Call — calls by tool'
                  isOptional: true
                }
                {
                  name: 'PartSubTitle'
                  value: applicationInsightsName
                  isOptional: true
                }
                {
                  name: 'Dimensions'
                  value: {
                    xAxis: {
                      name: 'tool'
                      type: 'string'
                    }
                    yAxis: [
                      {
                        name: 'count_'
                        type: 'long'
                      }
                    ]
                    aggregation: 'Sum'
                  }
                  isOptional: true
                }
                {
                  name: 'LegendOptions'
                  value: {
                    isEnabled: true
                    position: 'Bottom'
                  }
                  isOptional: true
                }
                {
                  name: 'IsQueryContainTimeRange'
                  value: false
                  isOptional: true
                }
              ]
              #disable-next-line BCP036
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              settings: {}
            }
          }
          // 5) Latency percentiles (p50/p95/p99) over time
          {
            position: { x: 0, y: 13, colSpan: 12, rowSpan: 4 }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                }
                {
                  name: 'Scope'
                  value: {
                    resourceIds: [appInsightsResourceId]
                  }
                  isOptional: true
                }
                {
                  name: 'PartId'
                  value: guid('tile5-${name}')
                  isOptional: true
                }
                {
                  name: 'Version'
                  value: '2.0'
                  isOptional: true
                }
                {
                  name: 'TimeRange'
                  value: timeRange
                  isOptional: true
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                }
                {
                  name: 'Query'
                  value: 'dependencies\n| where tostring(customDimensions["mcp.method.name"]) == "tools/call"\n| summarize p50 = percentile(duration, 50), p95 = percentile(duration, 95), p99 = percentile(duration, 99) by bin(timestamp, 5m)\n| order by timestamp asc\n| render timechart'
                  isOptional: true
                }
                {
                  name: 'ControlType'
                  value: 'FrameControlChart'
                  isOptional: true
                }
                {
                  name: 'SpecificChart'
                  value: 'Line'
                  isOptional: true
                }
                {
                  name: 'PartTitle'
                  value: 'Tools/Call — latency percentiles (ms)'
                  isOptional: true
                }
                {
                  name: 'PartSubTitle'
                  value: applicationInsightsName
                  isOptional: true
                }
                {
                  name: 'Dimensions'
                  value: {
                    xAxis: {
                      name: 'timestamp'
                      type: 'datetime'
                    }
                    yAxis: [
                      {
                        name: 'p50'
                        type: 'real'
                      }
                      {
                        name: 'p95'
                        type: 'real'
                      }
                      {
                        name: 'p99'
                        type: 'real'
                      }
                    ]
                    aggregation: 'Sum'
                  }
                  isOptional: true
                }
                {
                  name: 'LegendOptions'
                  value: {
                    isEnabled: true
                    position: 'Bottom'
                  }
                  isOptional: true
                }
                {
                  name: 'IsQueryContainTimeRange'
                  value: false
                  isOptional: true
                }
              ]
              #disable-next-line BCP036
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              settings: {}
            }
          }
          // 6) Failed requests (metric chart)
          {
            position: { x: 0, y: 1, colSpan: 6, rowSpan: 3 }
            metadata: any({
              type: 'Extension/HubsExtension/PartType/MonitorChartPart'
              inputs: [
                {
                  name: 'options'
                  value: {
                    chart: {
                      metrics: [
                        {
                          resourceMetadata: {
                            id: appInsightsResourceId
                          }
                          name: 'requests/failed'
                          aggregationType: 7
                          namespace: 'microsoft.insights/components'
                          metricVisualization: {
                            displayName: 'Failed requests'
                            color: '#EC008C'
                          }
                        }
                      ]
                      title: 'Failed requests'
                      visualization: {
                        chartType: 3
                        legendVisualization: {
                          isVisible: true
                          position: 2
                          hideSubtitle: false
                        }
                        axisVisualization: {
                          x: {
                            isVisible: true
                            axisType: 2
                          }
                          y: {
                            isVisible: true
                            axisType: 1
                          }
                        }
                      }
                      openBladeOnClick: {
                        openBlade: true
                        destinationBlade: {
                          extensionName: 'HubsExtension'
                          bladeName: 'ResourceMenuBlade'
                          parameters: {
                            id: appInsightsResourceId
                            menuid: 'failures'
                          }
                        }
                      }
                    }
                  }
                }
                {
                  name: 'sharedTimeRange'
                  isOptional: true
                }
              ]
              settings: {}
            })
          }
          // 7) Server response time (metric chart)
          {
            position: { x: 6, y: 1, colSpan: 6, rowSpan: 3 }
            metadata: any({
              type: 'Extension/HubsExtension/PartType/MonitorChartPart'
              inputs: [
                {
                  name: 'options'
                  value: {
                    chart: {
                      metrics: [
                        {
                          resourceMetadata: {
                            id: appInsightsResourceId
                          }
                          name: 'requests/duration'
                          aggregationType: 4
                          namespace: 'microsoft.insights/components'
                          metricVisualization: {
                            displayName: 'Server response time'
                            color: '#00BCF2'
                          }
                        }
                      ]
                      title: 'Server response time'
                      visualization: {
                        chartType: 2
                        legendVisualization: {
                          isVisible: true
                          position: 2
                          hideSubtitle: false
                        }
                        axisVisualization: {
                          x: {
                            isVisible: true
                            axisType: 2
                          }
                          y: {
                            isVisible: true
                            axisType: 1
                          }
                        }
                      }
                      openBladeOnClick: {
                        openBlade: true
                        destinationBlade: {
                          extensionName: 'HubsExtension'
                          bladeName: 'ResourceMenuBlade'
                          parameters: {
                            id: appInsightsResourceId
                            menuid: 'performance'
                          }
                        }
                      }
                    }
                  }
                }
                {
                  name: 'sharedTimeRange'
                  isOptional: true
                }
              ]
              settings: {}
            })
          }
          // 9) Failures curated blade tile
          {
            position: { x: 0, y: 0, colSpan: 6, rowSpan: 1 }
            metadata: any({
              inputs: [
                {
                  name: 'ResourceId'
                  value: appInsightsResourceId
                }
                {
                  name: 'DataModel'
                  value: {
                    version: '1.0.0'
                    timeContext: {
                      durationMs: 86400000
                      createdTime: '2018-05-04T23:42:40.072Z'
                      isInitialTime: false
                      grain: 1
                      useDashboardTimeRange: false
                    }
                  }
                  isOptional: true
                }
                {
                  name: 'ConfigurationId'
                  value: '8a02f7bf-ac0f-40e1-afe9-f0e72cfee77f'
                  isOptional: true
                }
              ]
              type: 'Extension/AppInsightsExtension/PartType/CuratedBladeFailuresPinnedPart'
              isAdapter: true
              asset: {
                idInputName: 'ResourceId'
                type: 'ApplicationInsights'
              }
              defaultMenuItemId: 'failures'
            })
          }
          // 10) Performance curated blade tile
          {
            position: { x: 6, y: 0, colSpan: 6, rowSpan: 1 }
            metadata: any({
              inputs: [
                {
                  name: 'ResourceId'
                  value: appInsightsResourceId
                }
                {
                  name: 'DataModel'
                  value: {
                    version: '1.0.0'
                    timeContext: {
                      durationMs: 86400000
                      createdTime: '2018-05-04T23:43:37.804Z'
                      isInitialTime: false
                      grain: 1
                      useDashboardTimeRange: false
                    }
                  }
                  isOptional: true
                }
                {
                  name: 'ConfigurationId'
                  value: '2a8ede4f-2bee-4b9c-aed9-2db0e8a01865'
                  isOptional: true
                }
              ]
              type: 'Extension/AppInsightsExtension/PartType/CuratedBladePerformancePinnedPart'
              isAdapter: true
              asset: {
                idInputName: 'ResourceId'
                type: 'ApplicationInsights'
              }
              defaultMenuItemId: 'performance'
            })
          }
        ]
        metadata: {}
      }
    ]
    metadata: {}
  }
}
