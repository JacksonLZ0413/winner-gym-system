App({
  globalData: {
    userInfo: null,
    token: null,
    baseUrl: 'http://localhost:5001/api'
  },

  onLaunch: function () {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    
    if (token && userInfo) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  },

  request: function (options) {
    const that = this
    const token = this.globalData.token
    
    if (!options.header) {
      options.header = {}
    }
    
    if (token && options.noAuth !== true) {
      options.header['Authorization'] = 'Bearer ' + token
    }
    
    options.url = this.globalData.baseUrl + options.url
    
    return new Promise(function (resolve, reject) {
      wx.request({
        url: options.url,
        method: options.method || 'GET',
        data: options.data,
        header: options.header,
        success: function (res) {
          if (res.data.code === 0) {
            resolve(res.data.data)
          } else if (res.data.code === 401) {
            that.globalData.token = null
            that.globalData.userInfo = null
            wx.removeStorageSync('token')
            wx.removeStorageSync('userInfo')
            wx.showToast({ title: '请重新登录', icon: 'none' })
            setTimeout(() => {
              wx.navigateTo({
                url: '/pages/login/login'
              })
            }, 1500)
            reject(res.data.message)
          } else {
            reject(res.data.message)
          }
        },
        fail: function (err) {
          reject('网络错误')
        }
      })
    })
  }
})