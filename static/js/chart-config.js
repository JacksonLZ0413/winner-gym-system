// Chart.js 配置

// 全局配置
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.color = 'rgba(255, 255, 255, 0.7)';

// 图表配置
const chartConfig = {
    // 预约趋势图配置
    bookingTrend: {
        type: 'line',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.8)'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            }
        }
    },

    // 教练绩效图配置
    coachPerformance: {
        type: 'bar',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.8)'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            }
        }
    }
};

// 图表实例
let bookingTrendChart = null;
let coachPerformanceChart = null;
let currentTimeRange = 'week';

function setTimeRange(range) {
    if (currentTimeRange === range) return;

    console.log('Setting time range to:', range);
    currentTimeRange = range;
    document.querySelectorAll('.time-range-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`.time-range-btn[data-range="${range}"]`).classList.add('active');

    const titleMap = {
        'today': '今日',
        'week': '本周',
        'month': '本月'
    };
    document.getElementById('trend-title').textContent = titleMap[range];

    fetchChartData(range);
}

function fetchChartData(range) {
    console.log('Fetching chart data for range:', range);
    fetch(`/admin/dashboard/chart_data?range=${range}`)
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data);
            updateCharts(data);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
        });
}

// 初始化图表
function initCharts() {
    // 预约趋势图
    const bookingTrendCtx = document.getElementById('bookingTrendChart');
    if (bookingTrendCtx) {
        try {
            const chartData = JSON.parse(bookingTrendCtx.dataset.data);
            const bookingData = chartData.booking_trend;
            
            bookingTrendChart = new Chart(bookingTrendCtx, {
                ...chartConfig.bookingTrend,
                data: {
                    labels: bookingData.labels,
                    datasets: [
                        {
                            label: '预约数',
                            data: bookingData.bookings,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.2)',
                            tension: 0.3,
                            fill: true
                        },
                        {
                            label: '完成数',
                            data: bookingData.completed,
                            borderColor: '#4ecca3',
                            backgroundColor: 'rgba(78, 204, 163, 0.2)',
                            tension: 0.3,
                            fill: true
                        }
                    ]
                }
            });
        } catch (error) {
            console.error('Error initializing booking trend chart:', error);
        }
    }

    // 教练绩效图
    const coachPerformanceCtx = document.getElementById('coachPerformanceChart');
    if (coachPerformanceCtx) {
        try {
            const chartData = JSON.parse(coachPerformanceCtx.dataset.data);
            const coachData = chartData.coach_performance;
            
            coachPerformanceChart = new Chart(coachPerformanceCtx, {
                ...chartConfig.coachPerformance,
                data: {
                    labels: coachData.coaches,
                    datasets: [
                        {
                            label: '课时数',
                            data: coachData.hours,
                            backgroundColor: 'rgba(102, 126, 234, 0.7)'
                        },
                        {
                            label: '预约率 (%)',
                            data: coachData.booking_rate,
                            backgroundColor: 'rgba(78, 204, 163, 0.7)'
                        }
                    ]
                }
            });
        } catch (error) {
            console.error('Error initializing coach performance chart:', error);
        }
    }
}

// 更新图表数据
function updateCharts(data) {
    if (bookingTrendChart) {
        const bookingData = data.booking_trend;
        bookingTrendChart.data.labels = bookingData.labels;
        bookingTrendChart.data.datasets[0].data = bookingData.bookings;
        bookingTrendChart.data.datasets[1].data = bookingData.completed;
        bookingTrendChart.update();
    }

    if (coachPerformanceChart) {
        const coachData = data.coach_performance;
        coachPerformanceChart.data.labels = coachData.coaches;
        coachPerformanceChart.data.datasets[0].data = coachData.hours;
        coachPerformanceChart.data.datasets[1].data = coachData.booking_rate;
        coachPerformanceChart.update();
    }
}

// 更新数据
function updateData() {
    fetch('/admin/dashboard', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.text())
    .then(html => {
        // 解析HTML，提取需要更新的数据
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // 更新今日关键指标
        const overviewCards = doc.querySelectorAll('.overview-card');
        if (overviewCards.length > 0) {
            const currentCards = document.querySelectorAll('.overview-card');
            overviewCards.forEach((card, index) => {
                if (currentCards[index]) {
                    currentCards[index].innerHTML = card.innerHTML;
                }
            });
        }
        
        // 更新实时监控数据
        const statusCards = doc.querySelectorAll('.status-card');
        if (statusCards.length > 0) {
            const currentStatusCards = document.querySelectorAll('.status-card');
            statusCards.forEach((card, index) => {
                if (currentStatusCards[index]) {
                    currentStatusCards[index].innerHTML = card.innerHTML;
                }
            });
        }
        
        // 更新近期动态
        const recentSection = doc.querySelector('.chart-card:nth-child(4)');
        if (recentSection) {
            const currentRecentSection = document.querySelector('.chart-card:nth-child(4)');
            if (currentRecentSection) {
                currentRecentSection.innerHTML = recentSection.innerHTML;
            }
        }
        
        // 更新图表数据
        const bookingTrendChart = doc.getElementById('bookingTrendChart');
        if (bookingTrendChart) {
            const chartData = JSON.parse(bookingTrendChart.dataset.data);
            updateCharts(chartData);
        }
        
        // 更新时间
        const dateElement = doc.querySelector('.header .date');
        if (dateElement) {
            const currentDateElement = document.querySelector('.header .date');
            if (currentDateElement) {
                currentDateElement.textContent = dateElement.textContent;
            }
        }
        
        console.log('数据已更新');
    })
    .catch(error => {
        console.error('Error updating data:', error);
    });
}

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    
    // 添加时间范围按钮的事件监听器
    document.querySelectorAll('.time-range-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const range = this.dataset.range;
            setTimeRange(range);
        });
    });
    
    // 每30秒自动更新数据
    setInterval(updateData, 30000);
    
    // 显示更新提示
    const updateIndicator = document.createElement('div');
    updateIndicator.id = 'update-indicator';
    updateIndicator.style.position = 'fixed';
    updateIndicator.style.bottom = '20px';
    updateIndicator.style.right = '20px';
    updateIndicator.style.backgroundColor = 'rgba(102, 126, 234, 0.9)';
    updateIndicator.style.color = 'white';
    updateIndicator.style.padding = '10px 15px';
    updateIndicator.style.borderRadius = '8px';
    updateIndicator.style.fontSize = '0.8rem';
    updateIndicator.style.zIndex = '1000';
    updateIndicator.style.opacity = '0';
    updateIndicator.style.transition = 'opacity 0.3s ease';
    updateIndicator.textContent = '数据已更新';
    document.body.appendChild(updateIndicator);
    
    // 更新时显示提示
    window.showUpdateMessage = function() {
        const indicator = document.getElementById('update-indicator');
        if (indicator) {
            indicator.style.opacity = '1';
            setTimeout(() => {
                indicator.style.opacity = '0';
            }, 2000);
        }
    };
});